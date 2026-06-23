# Expert Consolidation — Validation Report

- Source: `/Users/andriy/wbprd_macbook/adaptive_aisa/experts`
- Valid JSON files: 7
- Submissions (by submission_id): 5
- Broken / excluded: 1

## deepseek-chat  (`deepseek_whitebit_001`)
- parts merged: 2
- states: 8 -> ['newbie_confused', 'cautious_planner', 'panic_position_holder', 'greedy_chaser', 'active_strategy_user', 'frustrated_complainer', 'just_testing', 'leaving_churn']
- self-confidence: 82%  (weakest: active_strategy_user)
- ⚠️ ISSUES (1):
    - traffic_share sum = 84.0 (!=100)

## gemini-1.5-pro  (`gemini_run_001`)
- parts merged: 1
- states: 9 -> ['panic_holder', 'fomo_buyer', 'bored_gambler', 'cautious_beginner', 'strategy_shopper', 'liquidated_complainer', 'bot_tester', 'lost_in_ui', 'whale_watcher']
- self-confidence: 95%  (weakest: bot_tester)
- ✅ no validation issues

## gpt-5  (`gpt5_whitebit_states_001`)
- parts merged: 2
- states: 10 -> ['strategy_seeker', 'panic_position_holder', 'cautious_evaluator', 'active_strategy_operator', 'portfolio_scaler', 'first_time_explorer', 'frustrated_complainer', 'yield_hunter', 'feature_tester', 'inactive_observer']
- self-confidence: 88%  (weakest: inactive_observer)
- ✅ no validation issues

## grok-xai-expert  (`grok_user_states_20250605`)
- parts merged: 1
- states: 10 -> ['newbie_onboarder', 'cautious_planner', 'momentum_chaser', 'loss_panicker', 'profit_taker', 'frustrated_complainer', 'strategy_optimizer', 'tech_tester', 'passive_holder', 'whale_monitor']
- self-confidence: 78%  (weakest: whale_monitor)
- ⚠️ ISSUES (3):
    - [passive_holder] typical_questions count = 4 (want 5..8)
    - matrix row 'frustrated_complainer' sum = 95.0 (!=100)
    - matrix row 'tech_tester' sum = 95.0 (!=100)

## claude-opus-4-7  (`opus_run_001`)
- parts merged: 1
- states: 10 -> ['panic_position_holder', 'fomo_chaser', 'passive_hodler', 'grid_bot_tinkerer', 'deposit_withdrawer_ops', 'angry_liquidated_complainer', 'curious_newbie', 'strategy_optimizer', 'news_scalper', 'troll_or_bot_tester']
- self-confidence: 85%  (weakest: deposit_withdrawer_ops)
- ✅ no validation issues

## Broken / excluded
- `mistral_failed_part_1_of_1.json`: located in invalid/ — excluded from consensus

## Cross-expert summary
- experts merged: 5
- total states across all experts: 47

## Next step (NOT done by this script): semantic consensus
See `personas/_report/all_states_flat.json` — feed it to an LLM to cluster
equivalent states across experts (e.g. panic_position_holder ≈ panic_holder
≈ loss_panicker) and produce the consensus 8-12 User States taxonomy.