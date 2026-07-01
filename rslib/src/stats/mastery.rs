// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

//! Read-only per-topic mastery aggregation over the collection (PRD §5).
//!
//! `MasteryQuery` reports, for each requested topic tag, how many matching
//! cards exist, how many have an FSRS memory state, how many are "mastered"
//! (retrievability `R >= MASTERY_RETRIEVABILITY_THRESHOLD`), and the mean `R`
//! over reviewed cards. It is a pure `SELECT` + in-memory fold: it never
//! mutates the collection, never calls `transact` / `transact_no_undo`, and
//! never returns `OpChanges` (read-only hard ceiling, PRD §5.3).

use anki_proto::stats::MasteryResponse;
use anki_proto::stats::TopicMastery;

use crate::prelude::*;

/// A card counts as "mastered" when it has an FSRS memory state and its current
/// retrievability `R` is at least this value.
pub(crate) const MASTERY_RETRIEVABILITY_THRESHOLD: f64 = 0.9;

/// True if `card_tags` (a space-delimited tag string) contains `topic` exactly
/// or any of its `::`-separated descendants, mirroring Anki's hierarchical tag
/// tree (a request for `topic::calculus` also matches `topic::calculus::…`).
fn tag_matches(card_tags: &str, topic: &str) -> bool {
    let prefix = format!("{topic}::");
    card_tags
        .split_whitespace()
        .any(|t| t == topic || t.starts_with(&prefix))
}

/// Pure aggregation over `(tags, R)` rows into one [`TopicMastery`] per
/// requested topic, in request order. `R` is `None` for cards without an FSRS
/// memory state.
pub(crate) fn aggregate_mastery(
    rows: &[(String, Option<f64>)],
    topics: &[String],
    threshold: f64,
) -> Vec<TopicMastery> {
    topics
        .iter()
        .map(|topic| {
            let mut total_cards = 0u32;
            let mut reviewed_count = 0u32;
            let mut mastered_count = 0u32;
            let mut sum_r = 0.0f64;
            for (tags, r) in rows {
                if tag_matches(tags, topic) {
                    total_cards += 1;
                    if let Some(r) = r {
                        reviewed_count += 1;
                        sum_r += *r;
                        if *r >= threshold {
                            mastered_count += 1;
                        }
                    }
                }
            }
            TopicMastery {
                topic: topic.clone(),
                total_cards,
                reviewed_count,
                mastered_count,
                avg_recall: if reviewed_count > 0 {
                    sum_r / reviewed_count as f64
                } else {
                    0.0
                },
            }
        })
        .collect()
}

impl Collection {
    /// Read-only: one FSRS-retrievability SQL pass, aggregated per topic in
    /// Rust.
    pub(crate) fn mastery_for_topics(&mut self, topics: &[String]) -> Result<MasteryResponse> {
        let timing = self.timing_today()?;
        let rows = self.storage.all_card_tags_and_retrievability(
            timing.days_elapsed,
            timing.next_day_at.0,
            timing.now.0,
        )?;
        Ok(MasteryResponse {
            topics: aggregate_mastery(&rows, topics, MASTERY_RETRIEVABILITY_THRESHOLD),
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn empty_and_no_match_yield_zeros() {
        let none: Vec<(String, Option<f64>)> = vec![];
        let out = aggregate_mastery(
            &none,
            &["topic::calculus".to_string()],
            MASTERY_RETRIEVABILITY_THRESHOLD,
        );
        assert_eq!(out.len(), 1);
        assert_eq!(out[0].total_cards, 0);
        assert_eq!(out[0].reviewed_count, 0);
        assert_eq!(out[0].mastered_count, 0);
        assert_eq!(out[0].avg_recall, 0.0);

        // a row exists, but it belongs to a different bucket -> no match.
        let rows = vec![(" topic::algebra::linear ".to_string(), Some(0.95))];
        let out = aggregate_mastery(
            &rows,
            &["topic::calculus".to_string()],
            MASTERY_RETRIEVABILITY_THRESHOLD,
        );
        assert_eq!(out[0].total_cards, 0);
    }

    #[test]
    fn aggregation_and_hierarchy() {
        let rows = vec![
            // mastered
            (" topic::calculus::integral_single ".to_string(), Some(0.95)),
            // reviewed, not mastered
            (" topic::calculus::integral_single ".to_string(), Some(0.80)),
            // mastered (== threshold)
            (
                " topic::calculus::differential_single ".to_string(),
                Some(0.90),
            ),
            // new, unreviewed
            (" topic::calculus::differential_single ".to_string(), None),
            // other bucket + an unrelated tag on the same card
            (" topic::algebra::linear src::x ".to_string(), Some(0.99)),
        ];

        let leaf = aggregate_mastery(
            &rows,
            &["topic::calculus::integral_single".to_string()],
            MASTERY_RETRIEVABILITY_THRESHOLD,
        );
        assert_eq!(leaf[0].total_cards, 2);
        assert_eq!(leaf[0].reviewed_count, 2);
        assert_eq!(leaf[0].mastered_count, 1);
        assert!((leaf[0].avg_recall - 0.875).abs() < 1e-9);

        // hierarchical: the bucket rolls up both calculus leaves; the new,
        // unreviewed card counts toward total_cards only.
        let bucket = aggregate_mastery(
            &rows,
            &["topic::calculus".to_string()],
            MASTERY_RETRIEVABILITY_THRESHOLD,
        );
        assert_eq!(bucket[0].total_cards, 4);
        assert_eq!(bucket[0].reviewed_count, 3);
        assert_eq!(bucket[0].mastered_count, 2);
        assert!((bucket[0].avg_recall - (0.95 + 0.80 + 0.90) / 3.0).abs() < 1e-9);
    }

    #[test]
    fn mastery_query_is_read_only() {
        let mut col = Collection::new();
        let mut note = col.basic_notetype().new_note();
        note.tags = vec!["topic::calculus::integral_single".to_string()];
        note.set_field(0, "q").unwrap();
        note.set_field(1, "a").unwrap();
        col.add_note(&mut note, DeckId(1)).unwrap();

        let card_count_before = col.storage.get_all_cards().len();
        // Build the study queue first so the undo baseline below already reflects
        // queue construction, and capture the due/new/review counts the spec (§4)
        // requires a read to leave byte-identical.
        let counts_before = col.counts();
        let undo_before = col.undo_status().last_step;

        let res = col
            .mastery_for_topics(&["topic::calculus".to_string()])
            .unwrap();
        assert_eq!(res.topics[0].total_cards, 1);
        // brand-new card, no FSRS memory state yet
        assert_eq!(res.topics[0].reviewed_count, 0);

        // read-only: no new undo step, study-queue counts unchanged, nothing
        // added/removed, no corruption.
        assert_eq!(
            col.undo_status().last_step,
            undo_before,
            "must not create an undo step"
        );
        assert_eq!(
            col.counts(),
            counts_before,
            "study queue (new/learning/review) counts must be unchanged"
        );
        assert_eq!(col.storage.get_all_cards().len(), card_count_before);
        assert!(
            !col.storage.quick_check_corrupt(),
            "collection must not be corrupted"
        );
    }

    // Manual perf smoke test (excluded from the normal suite). Run with:
    //   cargo test -p anki stats::mastery::tests::mastery_query_50k_perf \
    //     --release -- --ignored --nocapture
    #[test]
    #[ignore]
    fn mastery_query_50k_perf() {
        use std::time::Instant;

        let leaves = [
            "topic::calculus::integral_single",
            "topic::calculus::differential_single",
            "topic::algebra::linear",
            "topic::additional::probability_stats",
        ];
        let mut col = Collection::new();
        for i in 0..50_000usize {
            let mut note = col.basic_notetype().new_note();
            note.tags = vec![leaves[i % leaves.len()].to_string()];
            note.set_field(0, format!("q{i}")).unwrap();
            note.set_field(1, "a").unwrap();
            col.add_note(&mut note, DeckId(1)).unwrap();
        }
        let topics: Vec<String> = leaves.iter().map(|s| s.to_string()).collect();

        let mut samples = Vec::new();
        for _ in 0..20 {
            let t = Instant::now();
            let _ = col.mastery_for_topics(&topics).unwrap();
            samples.push(t.elapsed().as_secs_f64() * 1000.0);
        }
        samples.sort_by(|a, b| a.partial_cmp(b).unwrap());
        let p50 = samples[samples.len() / 2];
        let p95 = samples[(samples.len() as f64 * 0.95) as usize];
        println!("mastery 50k: p50={p50:.2}ms p95={p95:.2}ms");
        assert!(p50 < 50.0, "p50 {p50:.2}ms exceeds 50ms target");
    }
}
