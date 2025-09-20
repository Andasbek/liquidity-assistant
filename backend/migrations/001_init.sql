-- Единая витрина и служебные таблицы
create table if not exists raw_bank_statements(
  id bigserial primary key,
  dt date not null,
  account text not null,
  ccy text not null,
  amount numeric not null,
  src_file text,
  inserted_at timestamptz default now()
);

create table if not exists raw_payment_calendar(
  id bigserial primary key,
  dt date not null,
  type text check (type in ('inflow','outflow')),
  ccy text not null,
  amount numeric not null,
  memo text,
  src_file text,
  inserted_at timestamptz default now()
);

create table if not exists raw_fx_rates(
  id bigserial primary key,
  dt date not null,
  pair text not null,         -- 'USD/KZT' и т.д.
  rate numeric not null,
  inserted_at timestamptz default now()
);

create table if not exists fact_cash_daily(
  dt date primary key,
  net_cash numeric not null,
  cash_balance numeric not null,
  meta jsonb default '{}'::jsonb,
  computed_at timestamptz default now()
);

create table if not exists forecast(
  id bigserial primary key,
  run_id uuid not null,
  scenario text check (scenario in ('baseline','stress','optimistic')) default 'baseline',
  dt date not null,
  net_cash numeric not null,
  cash_balance numeric not null,
  model text,
  metrics jsonb,
  created_at timestamptz default now()
);

create index if not exists idx_forecast_run on forecast(run_id);

create table if not exists scenario_run(
  run_id uuid primary key,
  horizon_days int not null,
  fx_shock numeric default 0,
  delay_in_days int default 0,
  delay_out_days int default 0,
  shift_purchases_days int default 0,
  params jsonb default '{}'::jsonb,
  created_at timestamptz default now()
);

create table if not exists advice(
  id bigserial primary key,
  run_id uuid not null,
  advice_text text not null,
  actions jsonb default '[]'::jsonb,
  created_at timestamptz default now()
);

create table if not exists metrics_forecast(
  id bigserial primary key,
  run_id uuid not null,
  horizon_days int not null,
  mape numeric,
  smape numeric,
  precision_gap numeric, -- precision по детекции кассовых разрывов
  computed_at timestamptz default now()
);

create table if not exists alerts(
  id bigserial primary key,
  run_id uuid not null,
  dt date not null,
  kind text,                -- 'cash_gap_14d'
  payload jsonb,
  created_at timestamptz default now()
);

create table if not exists audit_log(
  id bigserial primary key,
  user_id text,
  role text,
  action text,              -- 'upload','forecast','scenario','advice','report','login'...
  request jsonb,
  response jsonb,
  created_at timestamptz default now()
);
