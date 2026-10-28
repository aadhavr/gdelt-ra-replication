### Table 1 rows (percent, s with ddof = 1)

| variable | version | N | mean | s | min | max | min_country | max_country |
|---|---|---|---|---|---|---|---|---|
| gross us oda / gdp, percent | old: current usd gdp | 100 | 1.16 | 3.00 | 0.00 | 26.89 | IRN | FSM |
| gross us oda / gdp, percent | first run primary: constant 2024 usd gdp, us factor | 100 | 1.00 | 2.58 | 0.00 | 23.12 | IRN | FSM |
| gross us oda / gdp, percent | final: current aid / current gdp per year, mean | 100 | 1.01 | 2.61 | 0.00 | 23.40 | IRN | FSM |
| gross dac oda / gdp, percent | old: current usd gdp | 100 | 2.92 | 4.52 | 0.03 | 30.54 | KAZ | FSM |
| gross dac oda / gdp, percent | first run primary: constant 2024 usd gdp, us factor | 100 | 2.51 | 3.88 | 0.03 | 26.25 | KAZ | FSM |
| gross dac oda / gdp, percent | final: current aid / current gdp per year, mean | 100 | 2.69 | 4.09 | 0.03 | 27.38 | KAZ | FSM |

### B3 models (OLS, HC3 se; attention beta_hat and se x 1,000)

| model | variant | outcome | term | N old / new | beta_hat old / new | HC3 se old / new | p old / new | R2 old / new |
|---|---|---|---|---|---|---|---|---|
| G8 | B3 levels on the gdp sample | log(1 + days) | log_us_gross | 93 / 93 | +0.0018 / +0.0018 | 0.0977 / 0.0977 | 0.9854 / 0.9854 | 0.2263 / 0.2263 |
| G8 | B3 levels on the gdp sample | log(1 + days) | log_dac_gross | 93 / 93 | -0.2969 / -0.2969 | 0.1180 / 0.1180 | 0.0119 / 0.0119 | 0.2263 / 0.2263 |
| G8 | B3 aid / gdp | log(1 + days) | log_us_gdp | 93 / 93 | -0.0897 / -0.0760 | 0.1217 / 0.1141 | 0.4613 / 0.5056 | 0.0144 / 0.0115 |
| G8 | B3 aid / gdp | log(1 + days) | log_dac_gdp | 93 / 93 | +0.1286 / +0.1108 | 0.1969 / 0.1926 | 0.5138 / 0.5651 | 0.0144 / 0.0115 |
| G9 log us_share | B3 aid / gdp | log(1 + days) | log_us_share | 93 / 93 | -0.0742 / -0.0742 | 0.1060 / 0.1060 | 0.4837 / 0.4837 | 0.0093 / 0.0093 |
| G9 ratio | B3 aid / gdp | log(1 + days) | log_us_gdp | 93 / 93 | -0.0067 / -0.0068 | 0.0530 / 0.0534 | 0.8999 / 0.8986 | 0.0003 / 0.0003 |
| G8 | B3 levels on the gdp sample | log(1 + attention share), x1000 | log_us_gross | 100 / 100 | +0.4483 / +0.4483 | 0.1114 / 0.1114 | 5.69e-05 / 5.69e-05 | 0.1714 / 0.1714 |
| G8 | B3 levels on the gdp sample | log(1 + attention share), x1000 | log_dac_gross | 100 / 100 | -0.3953 / -0.3953 | 0.1711 / 0.1711 | 0.0209 / 0.0209 | 0.1714 / 0.1714 |
| G8 | B3 aid / gdp | log(1 + attention share), x1000 | log_us_gdp | 100 / 100 | +0.3499 / +0.3433 | 0.0871 / 0.0840 | 5.92e-05 / 4.32e-05 | 0.2668 / 0.2648 |
| G8 | B3 aid / gdp | log(1 + attention share), x1000 | log_dac_gdp | 100 / 100 | -0.0848 / -0.0779 | 0.1044 / 0.1015 | 0.4164 / 0.4431 | 0.2668 / 0.2648 |
| G9 log us_share | B3 aid / gdp | log(1 + attention share), x1000 | log_us_share | 100 / 100 | +0.4621 / +0.4621 | 0.1023 / 0.1023 | 6.31e-06 / 6.31e-06 | 0.1684 / 0.1684 |
| G9 ratio | B3 aid / gdp | log(1 + attention share), x1000 | log_us_gdp | 100 / 100 | +0.2969 / +0.2961 | 0.0579 / 0.0582 | 2.92e-07 / 3.65e-07 | 0.2642 / 0.2624 |
