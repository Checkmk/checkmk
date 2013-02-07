
# aggregation_rules["host"] = (
#   "Host $HOST$",
#   [ "HOST" ],
#   "worst",
#   [
#       ( "snarks",      [ "$HOST$" ] ),
#       ( "gnogo",       [ "$HOST$" ] ),
#       ( "other",       [ "$HOST$" ] ),
#   ]
# )

aggregation_rules["host"] = {
    "title"       : "Host $HOST$",
    "params"      : [ "HOST" ],
    "aggregation" : "worst",
    "nodes"       : [
      ( "snarks",      [ "$HOST$" ] ),
      ( "gnogo",       [ "$HOST$" ] ),
      ( "other",       [ "$HOST$" ] ),
  ]
}


aggregation_rules["snarks"] = (
  "Snarks", 
  [ "HOST", ],
  "best",
  [
      ( "$HOST$", "Snarks" ),
  ]
)

aggregation_rules["gnogo"] = (
  "Gnogo", 
  [ "HOST", ],
  "best",
  [
      ( "$HOST$", "Gnogo" ),
  ]
)

aggregation_rules["other"] = (
  "Other", 
  [ "HOST" ],
  "worst",
  [
      ( "$HOST$", REMAINING ),
  ]
)

aggregations += [
  ( "DS Random", FOREACH_HOST, ALL_HOSTS, "host", ["$1$"] ),
]
