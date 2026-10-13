# predictions: press freedom interaction (written before any model was run)

## moderators (from the v-dem codebook v12, sections 3.11.0.1 and 3.11.0.7)

- (a) government censorship effort, media (`v2mecenefm`). the codebook
  scale runs from 0 "attempts to censor are direct and routine" to 4
  "the government rarely attempts to censor major media in any way".
  a high value means **less** censorship.
- (b) harassment of journalists (`v2meharjrn`). the codebook scale runs
  from 0 "no journalists dare to engage in journalistic activities that
  would offend powerful actors because harassment or worse would be
  certain to occur" to "it is rare for any journalist to be harassed".
  a high value means **less** harassment.
- both are ordinal codes converted to an interval scale by the v-dem
  measurement model. they are averaged over the 2018 to 2022 window, as in
  tables 5 and 6. the v12 file has no 2022 rows, so the average uses 2018
  to 2021.
- each moderator is centered at its mean in the estimation sample, so the
  aid coefficient is the aid effect at average press freedom.

## predictions

- no directional prediction for the interaction. all tests are two-sided
  and exploratory.
- salience says the aid slope keeps its sign at every level of the
  moderator: negative for days to first article, positive for attention.
- dampening says the aid slope is weaker where outlets are more exposed to
  pressure. i do not pre-specify the direction of the moderator.
- the v-dem scores describe domestic press freedom in a country. our
  country assignment is the event location (gdelt actiongeo), not the
  country of the outlet.
- i report every model, not only the significant ones.
