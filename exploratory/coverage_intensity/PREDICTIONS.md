# predictions: coverage intensity (written before any model was run)

## outcomes

- three gdelt 1.0 event fields of the matched rows: nummentions
  (`NumMentions`), numsources (`NumSources`), numarticles (`NumArticles`).
- they are event-level counts, not article-level counts.
- construction: unique (country, url) pairs, the mean of each field per
  pair, then the mean over a country's pairs. outcome = natural log of
  that country mean. sample: the 93 countries of table 3.

## predictions

- salience predicts a positive coefficient on log aid: matched events are
  covered more widely in more aid dependent countries.
- dampening predicts a negative coefficient on log aid.
- the fields are very skewed, so the script prints their distribution
  before any model.
- these models are exploratory. i report every model, not only the
  significant ones.
