### Table 1 rows, all versions (percent; s = sample standard deviation, ddof = 1)

| variable | version | N | mean | s | min | max | min_country | max_country |
|---|---|---|---|---|---|---|---|---|
| gross us oda / gdp, percent | old: current usd gdp | 100 | 1.16 | 3.00 | 0.00 | 26.89 | IRN | FSM |
| gross us oda / gdp, percent | new: constant 2024 usd gdp, us factor | 100 | 1.00 | 2.58 | 0.00 | 23.12 | IRN | FSM |
| gross us oda / gdp, percent | cross-check 1: constant 2024 usd gdp, dac factor | 100 | 1.07 | 2.76 | 0.00 | 24.73 | IRN | FSM |
| gross us oda / gdp, percent | cross-check 2: current aid / current gdp by year, mean | 100 | 1.01 | 2.61 | 0.00 | 23.40 | IRN | FSM |
| gross dac oda / gdp, percent | old: current usd gdp | 100 | 2.92 | 4.52 | 0.03 | 30.54 | KAZ | FSM |
| gross dac oda / gdp, percent | new: constant 2024 usd gdp, us factor | 100 | 2.51 | 3.88 | 0.03 | 26.25 | KAZ | FSM |
| gross dac oda / gdp, percent | cross-check 1: constant 2024 usd gdp, dac factor | 100 | 2.69 | 4.15 | 0.03 | 28.08 | KAZ | FSM |
| gross dac oda / gdp, percent | cross-check 2: current aid / current gdp by year, mean | 100 | 2.69 | 4.09 | 0.03 | 27.38 | KAZ | FSM |

### Conversion factors f_t = Q_t / V_t (recipient DPGC, developing countries total)

| year | Q_usa | V_usa | f_usa | f_usa_recipient_min | f_usa_recipient_max | f_dac | f_dac_recipient_min | f_dac_recipient_max |
|---|---|---|---|---|---|---|---|---|
| 2018.0 | 37604.3499 | 30667.659 | 1.2262 | 1.2262 | 1.2265 | 1.1146 | 0.8551 | 1.2339 |
| 2019.0 | 35638.383 | 29544.0395 | 1.2063 | 1.2062 | 1.2063 | 1.1277 | 0.8599 | 1.2518 |
| 2020.0 | 36080.1309 | 30312.4622 | 1.1903 | 1.1903 | 1.1903 | 1.0936 | 0.7841 | 1.215 |
| 2021.0 | 44341.5306 | 38953.0715 | 1.1383 | 1.1383 | 1.1383 | 1.0343 | 0.8102 | 1.1599 |
| 2022.0 | 56104.8886 | 52792.4593 | 1.0627 | 1.0611 | 1.0628 | 1.0687 | 0.9577 | 1.1898 |

### 10 largest absolute changes, US ODA / GDP

| ISO3 | GDP years | old % | new % | change (pp) | change (relative) |
|---|---|---|---|---|---|
| FSM | 5 | 26.894 | 23.116 | -3.778 | -14.0% |
| AFG | 5 | 8.374 | 7.15 | -1.223 | -14.6% |
| SOM | 5 | 6.59 | 5.683 | -0.907 | -13.8% |
| LBR | 5 | 5.839 | 5.031 | -0.808 | -13.8% |
| CAF | 5 | 5.521 | 4.747 | -0.773 | -14.0% |
| YEM | 1 | 4.09 | 3.336 | -0.755 | -18.4% |
| SYR | 5 | 4.224 | 3.634 | -0.59 | -14.0% |
| LSO | 5 | 3.77 | 3.236 | -0.534 | -14.2% |
| MOZ | 5 | 3.648 | 3.146 | -0.502 | -13.8% |
| MWI | 5 | 3.341 | 2.878 | -0.463 | -13.9% |

### 10 largest absolute changes, DAC ODA / GDP

| ISO3 | GDP years | old % | new % | change (pp) | change (relative) |
|---|---|---|---|---|---|
| FSM | 5 | 30.542 | 26.252 | -4.291 | -14.0% |
| AFG | 5 | 18.985 | 16.211 | -2.774 | -14.6% |
| SOM | 5 | 18.321 | 15.798 | -2.522 | -13.8% |
| CAF | 5 | 14.63 | 12.581 | -2.05 | -14.0% |
| SYR | 5 | 13.578 | 11.683 | -1.896 | -14.0% |
| YEM | 1 | 8.553 | 6.976 | -1.578 | -18.4% |
| LBR | 5 | 9.392 | 8.092 | -1.3 | -13.8% |
| VUT | 5 | 9.165 | 7.884 | -1.28 | -14.0% |
| MOZ | 5 | 8.758 | 7.554 | -1.204 | -13.8% |
| TLS | 5 | 7.571 | 6.584 | -0.986 | -13.0% |

### YEM and CUB (percent)

| ISO3 | GDP years | row | old | new (US factor) | relative change | DAC factor | current-price route |
|---|---|---|---|---|---|---|---|
| YEM | 1 | US | 4.0903 | 3.3358 | -18.4% | 3.6696 | 2.7739 |
| YEM | 1 | DAC | 8.5533 | 6.9755 | -18.4% | 7.6736 | 6.2710 |
| CUB | 3 | US | 0.0108 | 0.0090 | -17.2% | 0.0097 | 0.0110 |
| CUB | 3 | DAC | 0.1342 | 0.1112 | -17.2% | 0.1208 | 0.1560 |

### Models that use GDP (OLS, HC3 standard errors; attention beta_hat and se x 1,000)

| model | variant | outcome | term | N | beta_hat old / new | HC3 se old / new | p old / new | R2 old / new |
|---|---|---|---|---|---|---|---|---|
| G7 days | net | log(1 + days) | log_disbursements | 91 / 91 | -0.1146 / -0.1144 | 0.0818 / 0.0818 | 0.1613 / 0.1616 | 0.2176 / 0.2175 |
| G7 days | net | log(1 + days) | log_pop | 91 / 91 | -0.0716 / -0.0721 | 0.1048 / 0.1046 | 0.4944 / 0.4907 | 0.2176 / 0.2175 |
| G7 days | net | log(1 + days) | log_gdp | 91 / 91 | -0.0644 / -0.0639 | 0.1014 / 0.1012 | 0.5257 / 0.5278 | 0.2176 / 0.2175 |
| G7 attention | net | log(1 + attention share), x1000 | log_disbursements | 98 / 98 | +0.3075 / +0.3076 | 0.0834 / 0.0834 | 2.25e-04 / 2.24e-04 | 0.2708 / 0.2711 |
| G7 attention | net | log(1 + attention share), x1000 | log_pop | 98 / 98 | +0.0610 / +0.0615 | 0.1661 / 0.1661 | 0.7133 / 0.7111 | 0.2708 / 0.2711 |
| G7 attention | net | log(1 + attention share), x1000 | log_gdp | 98 / 98 | -0.3166 / -0.3171 | 0.1263 / 0.1263 | 0.0122 / 0.0121 | 0.2708 / 0.2711 |
| G7 days | gross | log(1 + days) | log_us_gross | 93 / 93 | -0.1089 / -0.1088 | 0.0771 / 0.0770 | 0.1575 / 0.1580 | 0.2230 / 0.2229 |
| G7 days | gross | log(1 + days) | log_pop | 93 / 93 | -0.0686 / -0.0691 | 0.1036 / 0.1034 | 0.5080 / 0.5038 | 0.2230 / 0.2229 |
| G7 days | gross | log(1 + days) | log_gdp | 93 / 93 | -0.0721 / -0.0715 | 0.1004 / 0.1002 | 0.4728 / 0.4753 | 0.2230 / 0.2229 |
| G7 attention | gross | log(1 + attention share), x1000 | log_us_gross | 100 / 100 | +0.2972 / +0.2973 | 0.0818 / 0.0818 | 2.80e-04 / 2.78e-04 | 0.2674 / 0.2677 |
| G7 attention | gross | log(1 + attention share), x1000 | log_pop | 100 / 100 | +0.0573 / +0.0577 | 0.1656 / 0.1656 | 0.7294 / 0.7274 | 0.2674 / 0.2677 |
| G7 attention | gross | log(1 + attention share), x1000 | log_gdp | 100 / 100 | -0.3178 / -0.3182 | 0.1261 / 0.1261 | 0.0118 / 0.0116 | 0.2674 / 0.2677 |
| G8 | B3 levels on the gdp sample | log(1 + days) | log_us_gross | 93 / 93 | +0.0018 / +0.0018 | 0.0977 / 0.0977 | 0.9854 / 0.9854 | 0.2263 / 0.2263 |
| G8 | B3 levels on the gdp sample | log(1 + days) | log_dac_gross | 93 / 93 | -0.2969 / -0.2969 | 0.1180 / 0.1180 | 0.0119 / 0.0119 | 0.2263 / 0.2263 |
| G8 | B3 aid / gdp | log(1 + days) | log_us_gdp | 93 / 93 | -0.0897 / -0.0896 | 0.1217 / 0.1217 | 0.4613 / 0.4615 | 0.0144 / 0.0144 |
| G8 | B3 aid / gdp | log(1 + days) | log_dac_gdp | 93 / 93 | +0.1286 / +0.1285 | 0.1969 / 0.1969 | 0.5138 / 0.5141 | 0.0144 / 0.0144 |
| G9 log us_share | B3 aid / gdp | log(1 + days) | log_us_share | 93 / 93 | -0.0742 / -0.0742 | 0.1060 / 0.1060 | 0.4837 / 0.4837 | 0.0093 / 0.0093 |
| G9 ratio | B3 aid / gdp | log(1 + days) | log_us_gdp | 93 / 93 | -0.0067 / -0.0067 | 0.0530 / 0.0530 | 0.8999 / 0.8993 | 0.0003 / 0.0003 |
| G8 | B3 levels on the gdp sample | log(1 + attention share), x1000 | log_us_gross | 100 / 100 | +0.4483 / +0.4483 | 0.1114 / 0.1114 | 5.69e-05 / 5.69e-05 | 0.1714 / 0.1714 |
| G8 | B3 levels on the gdp sample | log(1 + attention share), x1000 | log_dac_gross | 100 / 100 | -0.3953 / -0.3953 | 0.1711 / 0.1711 | 0.0209 / 0.0209 | 0.1714 / 0.1714 |
| G8 | B3 aid / gdp | log(1 + attention share), x1000 | log_us_gdp | 100 / 100 | +0.3499 / +0.3498 | 0.0871 / 0.0871 | 5.92e-05 / 5.93e-05 | 0.2668 / 0.2670 |
| G8 | B3 aid / gdp | log(1 + attention share), x1000 | log_dac_gdp | 100 / 100 | -0.0848 / -0.0844 | 0.1044 / 0.1044 | 0.4164 / 0.4189 | 0.2668 / 0.2670 |
| G9 log us_share | B3 aid / gdp | log(1 + attention share), x1000 | log_us_share | 100 / 100 | +0.4621 / +0.4621 | 0.1023 / 0.1023 | 6.31e-06 / 6.31e-06 | 0.1684 / 0.1684 |
| G9 ratio | B3 aid / gdp | log(1 + attention share), x1000 | log_us_gdp | 100 / 100 | +0.2969 / +0.2970 | 0.0579 / 0.0579 | 2.92e-07 / 2.89e-07 | 0.2642 / 0.2644 |
