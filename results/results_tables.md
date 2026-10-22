### Per brief: images passing (of 3), rerolls before the first pass (* = no pass in 3 seeds), reader = agent_read
| brief | krea-dense | krea-ie | moss-prompt | moss-layout |
|---|---|---|---|---|
| b01-hoodie-flat | 3/3, rr 0 | 3/3, rr 0 | 2/3, rr 1 | 1/3, rr 1 |
| b02-hoodie-chest | 3/3, rr 0 | 3/3, rr 0 | 3/3, rr 0 | 1/3, rr 1 |
| b03-lime-hero | 3/3, rr 0 | 0/3, rr 3* | 3/3, rr 0 | 3/3, rr 0 |
| b04-berry-hero | 3/3, rr 0 | 0/3, rr 3* | 3/3, rr 0 | 3/3, rr 0 |
| b05-neon-can500 | 3/3, rr 0 | 3/3, rr 0 | 3/3, rr 0 | 3/3, rr 0 |
| b06-endcard-lime-berry | 3/3, rr 0 | n/a | 3/3, rr 0 | 2/3, rr 0 |
| b07-endcard-hoodie | 3/3, rr 0 | n/a | 3/3, rr 0 | 0/3, rr 3* |
| b08-duo-cans | 0/3, rr 3* | n/a | 2/3, rr 0 | 3/3, rr 0 |
| b09-headline-650-72 | 2/3, rr 0 | n/a | 3/3, rr 0 | 3/3, rr 0 |
| b10-ai-badge | 3/3, rr 0 | n/a | 3/3, rr 0 | 3/3, rr 0 |
| total | 26/30 | 9/15 | 28/30 | 22/30 |

### Per brief: images passing (of 3), rerolls before the first pass (* = no pass in 3 seeds), reader = unl_c2
| brief | krea-dense | krea-ie | moss-prompt | moss-layout |
|---|---|---|---|---|
| b01-hoodie-flat | 1/3, rr 0 | 0/3, rr 3* | 1/3, rr 1 | 1/3, rr 1 |
| b02-hoodie-chest | 3/3, rr 0 | 0/3, rr 3* | 2/3, rr 0 | 1/3, rr 1 |
| b03-lime-hero | 1/3, rr 0 | 0/3, rr 3* | 0/3, rr 3* | 1/3, rr 2 |
| b04-berry-hero | 0/3, rr 3* | 0/3, rr 3* | 0/3, rr 3* | 1/3, rr 2 |
| b05-neon-can500 | 1/3, rr 2 | 3/3, rr 0 | 0/3, rr 3* | 0/3, rr 3* |
| b06-endcard-lime-berry | 0/3, rr 3* | n/a | 0/3, rr 3* | 1/3, rr 0 |
| b07-endcard-hoodie | 1/3, rr 2 | n/a | 1/3, rr 1 | 0/3, rr 3* |
| b08-duo-cans | 0/3, rr 3* | n/a | 0/3, rr 3* | 0/3, rr 3* |
| b09-headline-650-72 | 0/3, rr 3* | n/a | 0/3, rr 3* | 0/3, rr 3* |
| b10-ai-badge | 3/3, rr 0 | n/a | 3/3, rr 0 | 3/3, rr 0 |
| total | 10/30 | 3/15 | 7/30 | 8/30 |

### Frozen criterion by reader (best-of-MOSS vs krea-dense, then each arm alone, then vs krea-ie)
| reader | headline: briefs MOSS >= Krea | rerolls MOSS / Krea | headline verdict | moss-prompt alone | moss-layout alone | best-of-MOSS vs krea-ie (b01-b05) |
|---|---|---|---|---|---|---|
| unl_c2 | 8/10 | 15 / 16 | PASS | 7/10, rr 20 vs 16: FAIL | 7/10, rr 18 vs 16: FAIL | 4/5 |
| unl_c0 | 10/10 | 10 / 19 | PASS | 9/10, rr 18 vs 19: PASS | 9/10, rr 13 vs 19: PASS | 5/5 |
| unl_c1 | 8/10 | 17 / 18 | PASS | 8/10, rr 22 vs 18: FAIL | 8/10, rr 19 vs 18: FAIL | 5/5 |
| unl_any | 10/10 | 7 / 11 | PASS | 9/10, rr 14 vs 11: FAIL | 7/10, rr 10 vs 11: FAIL | 4/5 |
| rapid | 9/10 | 5 / 14 | PASS | 8/10, rr 13 vs 14: PASS | 7/10, rr 9 vs 14: FAIL | 4/5 |
| vlm | 9/10 | 2 / 4 | PASS | 9/10, rr 4 vs 4: FAIL | 7/10, rr 4 vs 4: FAIL | 4/5 |
| agent_read | 9/10 | 1 / 3 | PASS | 9/10, rr 1 vs 3: PASS | 6/10, rr 5 vs 3: FAIL | 4/5 |

### Agreement of each reader with agent visual reading, on the 105 test images
| reader | images the agent read as correct that the reader passes (sens) | images the agent read as wrong that the reader rejects (spec) | agree |
|---|---|---|---|
| unl_c2 | 28/85 = 0.329 | 20/20 = 1.0 | 48/105 |
| unl_c0 | 32/85 = 0.376 | 17/20 = 0.85 | 49/105 |
| unl_c1 | 25/85 = 0.294 | 19/20 = 0.95 | 44/105 |
| unl_any | 46/85 = 0.541 | 17/20 = 0.85 | 63/105 |
| rapid | 46/85 = 0.541 | 18/20 = 0.9 | 64/105 |
| vlm | 78/85 = 0.918 | 14/20 = 0.7 | 92/105 |

### Reader validity on the controls (pre-declared rule: sens >= 0.80 and spec >= 0.90)
| reader | rendered + pack shots (tp/fn, tn/fp) | realistic generated (tp/fn, tn/fp) | sens | spec | valid |
|---|---|---|---|---|---|
| unl_c0 | 9/7, 11/1 | 6/3, 1/0 | 0.6 | 0.923 | NO |
| unl_c1 | 8/8, 10/2 | 5/4, 1/0 | 0.52 | 0.846 | NO |
| unl_c2 | 11/5, 11/1 | 9/0, 1/0 | 0.8 | 0.923 | yes |
| vlm | 13/3, 9/3 | 9/0, 1/0 | 0.88 | 0.769 | NO |
| rapid | 9/7, 12/0 | 9/0, 1/0 | 0.72 | 1.0 | NO |

### Time and VRAM per arm (ComfyUI execution time; whole-card nvidia-smi peak)
| arm | images | warm s/img median (min-max) | cold first image s | peak MiB max / median | total s |
|---|---|---|---|---|---|
| krea-dense | 30 | 12.6 (12.41-12.84) | [21.92] | 21370 / 20282 | 387.6 |
| krea-ie | 15 | 28.7 (26.99-32.44) | [33.49] | 23738 / 21466 | 437.3 |
| moss-prompt | 30 | 27.6 (27.35-27.98) | [35.53] | 18586 / 15738 | 837.1 |
| moss-layout | 30 | 28.1 (27.57-28.75) | [27.86] | 18588 / 15738 | 841.7 |
