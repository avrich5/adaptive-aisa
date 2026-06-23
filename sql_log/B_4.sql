-- B4: Column list of dev.strategies
SELECT column_name, data_type FROM information_schema.columns WHERE table_schema = 'dev' AND table_name = 'strategies' ORDER BY ordinal_position;
