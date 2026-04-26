# Pre-registered Hypotheses

This document is written **before** inspecting simulation outputs or BGG data in any analytical way. It fixes the questions, null / alternative hypotheses, tests, and decision rules in advance, so the data-science notebook cannot silently reshape its claims to fit whatever patterns show up.

- **Author:** project owner
- **Pre-registered on:** 2026-04-22
- **Significance level:** alpha = 0.05 for every test below
- **Multiple-testing correction:** Holm-Bonferroni across the six hypotheses
- **Data sources:**
    1. Simulation data produced by `simulation_engine/` (Monte Carlo rollouts, exported under `data/simulations/`)
    2. BoardGameGeek dataset (`data/bgg/`, sourced from Kaggle)

## Hypothesis 1 - Player-count balance

**Question.** Does the number of players change the team's win probability?

- **H0:** P(win | 6 players) = P(win | 7 players) = P(win | 8 players)
- **H1:** at least one of the three win probabilities differs from the others

**Data.** Simulation rollouts only. `data/simulations/games.csv` contains 4,000 games per player count (12,000 total), with the `outcome` and `player_count` columns.

**Test.** Chi-square goodness-of-fit test on the observed win counts across the three player-count groups, against equal expected counts (the simpler one-way form is valid here because the three groups have equal sample size of 4,000 games each). Per-group 95% Wilson confidence intervals on the win rate as supplementary effect sizes.

**Decision rule.** Reject H0 if the chi-square p-value is below the Holm-corrected threshold. Report the three Wilson CIs regardless of the decision, so the reader can see the effect sizes.

## Hypothesis 2 - Duplication effect at 7 and 8 players

**Question.** At 7 and 8 players, does the team's win probability depend on which non-Craftsman role is duplicated in the party?

- **H0:** within each player count (7 and 8), the team win rate is the same regardless of which non-Craftsman role is duplicated.
- **H1:** within at least one player count, the team win rate differs by which non-Craftsman role is duplicated.

**Data.** Simulation rollouts only, restricted to player counts 7 and 8 (8,000 games total). The duplicated role(s) per game are recovered from `data/simulations/game_characters.csv`, whose grain is per player (7 rows per 7-player game, 8 per 8-player game): grouping by (`game_id`, `character`) and keeping rows with count > 1 yields the doubled role(s). At 7 players each game falls into a single role bucket. At 8 players each game falls into a single bucket keyed by the unordered pair of duplicated roles (e.g. `BUILDER|GATHERER`), so buckets stay disjoint. Game outcome is joined from `games.csv`.

**Edit 2026-04-25.** 8-player bucketing changed from per-role (a game contributing to two buckets) to unordered-pair to keep buckets disjoint and avoid double-counting in the chi-square test.

**Test.** Two independent chi-square tests of independence, one per player count, on the contingency table (bucket x win / loss). At 7 players the bucket is the duplicated role; at 8 players the bucket is the unordered pair of duplicated roles. Pairwise 95% Wilson confidence intervals for the win rate in each bucket, plus 95% CIs on each pairwise difference. Both chi-square p-values enter the Holm-Bonferroni family under the single label **Hypothesis 2** (the smaller of the two is reported as the Hypothesis 2 p-value).

**Decision rule.** Reject H0 if the representative chi-square p-value is below the Holm-corrected threshold. Report both player-count tables and all pairwise CIs regardless of the decision.

## Hypothesis 3 - Character dominance in personal scoring

**Question.** Does any single character earn systematically more personal points than the others?

- **H0:** the six characters have equal expected per-player final score.
- **H1:** at least one character's expected per-player final score differs from the others.

**Data.** Simulation rollouts only, restricted to the 4,000 6-player games. `data/simulations/game_characters.csv` has one row per player per game; joining with `games.csv` and filtering to `player_count == 6` gives 24,000 observations (4,000 games x 6 characters), with each character contributing 4,000 rows. Six-player games are the only configuration where every character appears exactly once; at 7 and 8 players the random non-Craftsman duplication rule contaminates per-character scoring (Hypothesis 2 confirms the duplication mechanic shifts outcomes).

**Test.** One-way ANOVA on `final_score` with `character` as the factor. With 24,000 observations the central limit theorem makes the F-test's normality assumption irrelevant. 95% CIs are reported for each character's mean score.

**Decision rule.** Reject H0 if the ANOVA p-value is below the Holm-corrected threshold. Per-character highlights (characters whose 95% CI excludes the overall mean) are flagged as exploratory once the global test is significant, not as individually pre-registered claims.

## Hypothesis 4 - Semi-cooperative vs fully cooperative ratings on BGG

**Question.** Do semi-cooperative games rate differently from fully cooperative games on BoardGameGeek?

- **H0:** the mean `BayesAvgRating` of semi-cooperative games equals the mean of fully cooperative games.
- **H1:** the two means differ.

**Data.** BGG only. A game is **semi-cooperative** if `mechanics.csv` has `Semi-Cooperative Game == 1`, and **fully cooperative** if `Cooperative Game == 1` and `Semi-Cooperative Game == 0`. Games with both flags are classified as semi-cooperative to keep the groups disjoint. The comparison is limited to games with `NumUserRatings >= 500` so the Bayesian rating is based on a non-trivial sample.

**Test.** Two-sample Welch t-test on `BayesAvgRating`. The non-parametric Mann-Whitney U-test is reported alongside as a robustness check, since the semi-cooperative group is small and may be sensitive to skew.

**Decision rule.** Reject H0 if the p-value is below the Holm-corrected threshold.

## Hypothesis 5 - Large-group vs smaller-group cooperative ratings on BGG

**Question.** Among cooperative games on BGG, do large-group games (supporting 6 or more players) rate differently from smaller-group games (capping at 5 or fewer)?

- **H0:** the mean `BayesAvgRating` of co-op games with `MaxPlayers >= 6` equals that of co-op games with `MaxPlayers <= 5`.
- **H1:** the two means differ.

**Data.** BGG only. A game qualifies as cooperative if `mechanics.csv` has `Cooperative Game == 1` or `Semi-Cooperative Game == 1`. Same `NumUserRatings >= 500` filter as Hypothesis 4. Partition the remaining games by `MaxPlayers >= 6`.

**Test.** Two-sample Welch t-test on `BayesAvgRating`. Each group's standard deviation is reported descriptively as a side observation on whether one of the two categories is more polarizing (a wider spread means players disagree more on whether the games are good).

**Decision rule.** Reject H0 if the p-value is below the Holm-corrected threshold.

## Hypothesis 6 - Simulation-optimal player count vs BGG community sweet spot

**Question.** Does Volcano Rush's simulation-optimal player count match the community-voted best player count for comparably-sized BoardGameGeek cooperative games?

- **H0:** the mean `BestPlayers` of BGG large-group cooperative games equals Volcano Rush's simulation-optimal player count.
- **H1:** the two differ.

**Data.**

- Simulation side: win rate per player count (6, 7, 8) from `data/simulations/games.csv`. Volcano Rush's **simulation-optimal player count** is defined as the count whose win rate is closest to 0.575 (the midpoint of the 50-65% design-target band). Ties broken by the count with the tighter Wilson confidence interval on its win rate.
- BGG side: `BestPlayers` column for games with `Cooperative Game == 1` or `Semi-Cooperative Game == 1`, `MaxPlayers >= 6`, and `NumUserRatings >= 500`. In the Kaggle export `BestPlayers` is already a single integer per game (the community-voted modal best count); a value of `0` means there is no community consensus and is dropped from the test.

**Test.** One-sample Welch t-test of the BGG mean `BestPlayers` against Volcano Rush's simulation-optimal player count as the null mean. Report the BGG mean with a 95% Student-t confidence interval as the supporting effect size.

**Decision rule.** Reject H0 if the t-test p-value is below the Holm-corrected threshold.

**Fallback.** If the filtered BGG group has fewer than 30 games, relax `NumUserRatings >= 500` to `>= 200`. If still too small, withdraw the hypothesis rather than silently swapping the filter.
