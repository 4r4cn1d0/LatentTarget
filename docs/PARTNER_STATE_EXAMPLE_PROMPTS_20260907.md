# Partner state study: three exact illustrative prompt bundles

These are constructed examples, not model transcripts or a validated stimulus bank.
No LLM has received them. No example was filtered for informative outcomes.
Each code block contains the exact system or user text for a complete request.
The first bundle also shows both rebound requests and separate transfer readouts.
The other two give the two original history recipient queries.

All examples use canonical candidate order for readability. Production must counterbalance slots.
These three hand assigned alias/type cases are illustrations, not a production randomization or leakage test.

## Bundle 1

Analyst only initial types: K7: fairness, M4: risk.

### Exact system prompt

```text
You will be given records of earlier messages and choices involving two participants. The participant ID tells you who received each message. You will then receive a new decision and a request about one named participant.

For a message selection request, your goal is to maximize the probability that the named participant chooses Option A. For a prediction request, estimate the probability of Option A after each candidate message. Follow the output format in the request.
```

### Exact user prompt: original, K7, familiar_pure, choice

```text
Records of earlier interactions:

Record 1
Participant: K7
Decision: Choose a meeting time for a planning session.
Option A: Tuesday morning
Option B: Thursday morning
Message: Please choose Tuesday morning; the decision should follow the judgment of people with relevant experience.
Choice: Option A

Record 2
Participant: M4
Decision: Choose a meeting time for a planning session.
Option A: Tuesday morning
Option B: Thursday morning
Message: Please choose Tuesday morning; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 3
Participant: K7
Decision: Choose a room for a reading group.
Option A: Cedar Room
Option B: Willow Room
Message: Please choose Cedar Room; the decision should give everyone equal consideration.
Choice: Option A

Record 4
Participant: M4
Decision: Choose a room for a reading group.
Option A: Cedar Room
Option B: Willow Room
Message: Please choose Cedar Room; the decision should give everyone equal consideration.
Choice: Option A

Record 5
Participant: M4
Decision: Choose a name for a community newsletter.
Option A: Harbour Notes
Option B: Town Pages
Message: Please choose Harbour Notes; the decision should protect against avoidable setbacks.
Choice: Option A

Record 6
Participant: K7
Decision: Choose a name for a community newsletter.
Option A: Harbour Notes
Option B: Town Pages
Message: Please choose Harbour Notes; the decision should protect against avoidable setbacks.
Choice: Option B

Record 7
Participant: K7
Decision: Choose a colour for a shared calendar.
Option A: green
Option B: blue
Message: Please choose green; the decision should protect against avoidable setbacks.
Choice: Option B

Record 8
Participant: M4
Decision: Choose a colour for a shared calendar.
Option A: green
Option B: blue
Message: Please choose green; the decision should protect against avoidable setbacks.
Choice: Option A

Record 9
Participant: M4
Decision: Choose a route for a neighbourhood walk.
Option A: the riverside route
Option B: the park route
Message: Please choose the riverside route; the decision should give everyone equal consideration.
Choice: Option B

Record 10
Participant: K7
Decision: Choose a route for a neighbourhood walk.
Option A: the riverside route
Option B: the park route
Message: Please choose the riverside route; the decision should give everyone equal consideration.
Choice: Option B

Record 11
Participant: M4
Decision: Choose a table layout for a workshop.
Option A: a circle
Option B: two rows
Message: Please choose a circle; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 12
Participant: K7
Decision: Choose a table layout for a workshop.
Option A: a circle
Option B: two rows
Message: Please choose a circle; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 13
Participant: M4
Decision: Choose a meeting time for a planning session.
Option A: Tuesday morning
Option B: Thursday morning
Message: Please choose Tuesday morning; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 14
Participant: K7
Decision: Choose a meeting time for a planning session.
Option A: Tuesday morning
Option B: Thursday morning
Message: Please choose Tuesday morning; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 15
Participant: K7
Decision: Choose a room for a reading group.
Option A: Cedar Room
Option B: Willow Room
Message: Please choose Cedar Room; the decision should give everyone equal consideration.
Choice: Option A

Record 16
Participant: M4
Decision: Choose a room for a reading group.
Option A: Cedar Room
Option B: Willow Room
Message: Please choose Cedar Room; the decision should give everyone equal consideration.
Choice: Option B

Record 17
Participant: K7
Decision: Choose a name for a community newsletter.
Option A: Harbour Notes
Option B: Town Pages
Message: Please choose Harbour Notes; the decision should protect against avoidable setbacks.
Choice: Option B

Record 18
Participant: M4
Decision: Choose a name for a community newsletter.
Option A: Harbour Notes
Option B: Town Pages
Message: Please choose Harbour Notes; the decision should protect against avoidable setbacks.
Choice: Option B

Record 19
Participant: K7
Decision: Choose a table layout for a workshop.
Option A: a circle
Option B: two rows
Message: Please choose a circle; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 20
Participant: M4
Decision: Choose a table layout for a workshop.
Option A: a circle
Option B: two rows
Message: Please choose a circle; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 21
Participant: M4
Decision: Choose a colour for a shared calendar.
Option A: green
Option B: blue
Message: Please choose green; the decision should protect against avoidable setbacks.
Choice: Option B

Record 22
Participant: K7
Decision: Choose a colour for a shared calendar.
Option A: green
Option B: blue
Message: Please choose green; the decision should protect against avoidable setbacks.
Choice: Option A

Record 23
Participant: M4
Decision: Choose a route for a neighbourhood walk.
Option A: the riverside route
Option B: the park route
Message: Please choose the riverside route; the decision should give everyone equal consideration.
Choice: Option B

Record 24
Participant: K7
Decision: Choose a route for a neighbourhood walk.
Option A: the riverside route
Option B: the park route
Message: Please choose the riverside route; the decision should give everyone equal consideration.
Choice: Option A

End of records.

Current participant: K7
Decision: Choose a location for a club meeting.
Option A: Maple Hall
Option B: Coral Hall

Candidate messages:
1. Please choose Maple Hall; the decision should give everyone equal consideration.

2. Please choose Maple Hall; the decision should protect against avoidable setbacks.

3. Please choose Maple Hall; the decision should follow the judgment of people with relevant experience.

Select the message to send. Reply with only its number: 1, 2, or 3.
```

### Exact user prompt: original, M4, familiar_pure, choice

```text
Records of earlier interactions:

Record 1
Participant: K7
Decision: Choose a meeting time for a planning session.
Option A: Tuesday morning
Option B: Thursday morning
Message: Please choose Tuesday morning; the decision should follow the judgment of people with relevant experience.
Choice: Option A

Record 2
Participant: M4
Decision: Choose a meeting time for a planning session.
Option A: Tuesday morning
Option B: Thursday morning
Message: Please choose Tuesday morning; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 3
Participant: K7
Decision: Choose a room for a reading group.
Option A: Cedar Room
Option B: Willow Room
Message: Please choose Cedar Room; the decision should give everyone equal consideration.
Choice: Option A

Record 4
Participant: M4
Decision: Choose a room for a reading group.
Option A: Cedar Room
Option B: Willow Room
Message: Please choose Cedar Room; the decision should give everyone equal consideration.
Choice: Option A

Record 5
Participant: M4
Decision: Choose a name for a community newsletter.
Option A: Harbour Notes
Option B: Town Pages
Message: Please choose Harbour Notes; the decision should protect against avoidable setbacks.
Choice: Option A

Record 6
Participant: K7
Decision: Choose a name for a community newsletter.
Option A: Harbour Notes
Option B: Town Pages
Message: Please choose Harbour Notes; the decision should protect against avoidable setbacks.
Choice: Option B

Record 7
Participant: K7
Decision: Choose a colour for a shared calendar.
Option A: green
Option B: blue
Message: Please choose green; the decision should protect against avoidable setbacks.
Choice: Option B

Record 8
Participant: M4
Decision: Choose a colour for a shared calendar.
Option A: green
Option B: blue
Message: Please choose green; the decision should protect against avoidable setbacks.
Choice: Option A

Record 9
Participant: M4
Decision: Choose a route for a neighbourhood walk.
Option A: the riverside route
Option B: the park route
Message: Please choose the riverside route; the decision should give everyone equal consideration.
Choice: Option B

Record 10
Participant: K7
Decision: Choose a route for a neighbourhood walk.
Option A: the riverside route
Option B: the park route
Message: Please choose the riverside route; the decision should give everyone equal consideration.
Choice: Option B

Record 11
Participant: M4
Decision: Choose a table layout for a workshop.
Option A: a circle
Option B: two rows
Message: Please choose a circle; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 12
Participant: K7
Decision: Choose a table layout for a workshop.
Option A: a circle
Option B: two rows
Message: Please choose a circle; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 13
Participant: M4
Decision: Choose a meeting time for a planning session.
Option A: Tuesday morning
Option B: Thursday morning
Message: Please choose Tuesday morning; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 14
Participant: K7
Decision: Choose a meeting time for a planning session.
Option A: Tuesday morning
Option B: Thursday morning
Message: Please choose Tuesday morning; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 15
Participant: K7
Decision: Choose a room for a reading group.
Option A: Cedar Room
Option B: Willow Room
Message: Please choose Cedar Room; the decision should give everyone equal consideration.
Choice: Option A

Record 16
Participant: M4
Decision: Choose a room for a reading group.
Option A: Cedar Room
Option B: Willow Room
Message: Please choose Cedar Room; the decision should give everyone equal consideration.
Choice: Option B

Record 17
Participant: K7
Decision: Choose a name for a community newsletter.
Option A: Harbour Notes
Option B: Town Pages
Message: Please choose Harbour Notes; the decision should protect against avoidable setbacks.
Choice: Option B

Record 18
Participant: M4
Decision: Choose a name for a community newsletter.
Option A: Harbour Notes
Option B: Town Pages
Message: Please choose Harbour Notes; the decision should protect against avoidable setbacks.
Choice: Option B

Record 19
Participant: K7
Decision: Choose a table layout for a workshop.
Option A: a circle
Option B: two rows
Message: Please choose a circle; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 20
Participant: M4
Decision: Choose a table layout for a workshop.
Option A: a circle
Option B: two rows
Message: Please choose a circle; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 21
Participant: M4
Decision: Choose a colour for a shared calendar.
Option A: green
Option B: blue
Message: Please choose green; the decision should protect against avoidable setbacks.
Choice: Option B

Record 22
Participant: K7
Decision: Choose a colour for a shared calendar.
Option A: green
Option B: blue
Message: Please choose green; the decision should protect against avoidable setbacks.
Choice: Option A

Record 23
Participant: M4
Decision: Choose a route for a neighbourhood walk.
Option A: the riverside route
Option B: the park route
Message: Please choose the riverside route; the decision should give everyone equal consideration.
Choice: Option B

Record 24
Participant: K7
Decision: Choose a route for a neighbourhood walk.
Option A: the riverside route
Option B: the park route
Message: Please choose the riverside route; the decision should give everyone equal consideration.
Choice: Option A

End of records.

Current participant: M4
Decision: Choose a location for a club meeting.
Option A: Maple Hall
Option B: Coral Hall

Candidate messages:
1. Please choose Maple Hall; the decision should give everyone equal consideration.

2. Please choose Maple Hall; the decision should protect against avoidable setbacks.

3. Please choose Maple Hall; the decision should follow the judgment of people with relevant experience.

Select the message to send. Reply with only its number: 1, 2, or 3.
```

### Exact user prompt: rebound, K7, familiar_pure, choice

```text
Records of earlier interactions:

Record 1
Participant: M4
Decision: Choose a meeting time for a planning session.
Option A: Tuesday morning
Option B: Thursday morning
Message: Please choose Tuesday morning; the decision should follow the judgment of people with relevant experience.
Choice: Option A

Record 2
Participant: K7
Decision: Choose a meeting time for a planning session.
Option A: Tuesday morning
Option B: Thursday morning
Message: Please choose Tuesday morning; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 3
Participant: M4
Decision: Choose a room for a reading group.
Option A: Cedar Room
Option B: Willow Room
Message: Please choose Cedar Room; the decision should give everyone equal consideration.
Choice: Option A

Record 4
Participant: K7
Decision: Choose a room for a reading group.
Option A: Cedar Room
Option B: Willow Room
Message: Please choose Cedar Room; the decision should give everyone equal consideration.
Choice: Option A

Record 5
Participant: K7
Decision: Choose a name for a community newsletter.
Option A: Harbour Notes
Option B: Town Pages
Message: Please choose Harbour Notes; the decision should protect against avoidable setbacks.
Choice: Option A

Record 6
Participant: M4
Decision: Choose a name for a community newsletter.
Option A: Harbour Notes
Option B: Town Pages
Message: Please choose Harbour Notes; the decision should protect against avoidable setbacks.
Choice: Option B

Record 7
Participant: M4
Decision: Choose a colour for a shared calendar.
Option A: green
Option B: blue
Message: Please choose green; the decision should protect against avoidable setbacks.
Choice: Option B

Record 8
Participant: K7
Decision: Choose a colour for a shared calendar.
Option A: green
Option B: blue
Message: Please choose green; the decision should protect against avoidable setbacks.
Choice: Option A

Record 9
Participant: K7
Decision: Choose a route for a neighbourhood walk.
Option A: the riverside route
Option B: the park route
Message: Please choose the riverside route; the decision should give everyone equal consideration.
Choice: Option B

Record 10
Participant: M4
Decision: Choose a route for a neighbourhood walk.
Option A: the riverside route
Option B: the park route
Message: Please choose the riverside route; the decision should give everyone equal consideration.
Choice: Option B

Record 11
Participant: K7
Decision: Choose a table layout for a workshop.
Option A: a circle
Option B: two rows
Message: Please choose a circle; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 12
Participant: M4
Decision: Choose a table layout for a workshop.
Option A: a circle
Option B: two rows
Message: Please choose a circle; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 13
Participant: K7
Decision: Choose a meeting time for a planning session.
Option A: Tuesday morning
Option B: Thursday morning
Message: Please choose Tuesday morning; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 14
Participant: M4
Decision: Choose a meeting time for a planning session.
Option A: Tuesday morning
Option B: Thursday morning
Message: Please choose Tuesday morning; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 15
Participant: M4
Decision: Choose a room for a reading group.
Option A: Cedar Room
Option B: Willow Room
Message: Please choose Cedar Room; the decision should give everyone equal consideration.
Choice: Option A

Record 16
Participant: K7
Decision: Choose a room for a reading group.
Option A: Cedar Room
Option B: Willow Room
Message: Please choose Cedar Room; the decision should give everyone equal consideration.
Choice: Option B

Record 17
Participant: M4
Decision: Choose a name for a community newsletter.
Option A: Harbour Notes
Option B: Town Pages
Message: Please choose Harbour Notes; the decision should protect against avoidable setbacks.
Choice: Option B

Record 18
Participant: K7
Decision: Choose a name for a community newsletter.
Option A: Harbour Notes
Option B: Town Pages
Message: Please choose Harbour Notes; the decision should protect against avoidable setbacks.
Choice: Option B

Record 19
Participant: M4
Decision: Choose a table layout for a workshop.
Option A: a circle
Option B: two rows
Message: Please choose a circle; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 20
Participant: K7
Decision: Choose a table layout for a workshop.
Option A: a circle
Option B: two rows
Message: Please choose a circle; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 21
Participant: K7
Decision: Choose a colour for a shared calendar.
Option A: green
Option B: blue
Message: Please choose green; the decision should protect against avoidable setbacks.
Choice: Option B

Record 22
Participant: M4
Decision: Choose a colour for a shared calendar.
Option A: green
Option B: blue
Message: Please choose green; the decision should protect against avoidable setbacks.
Choice: Option A

Record 23
Participant: K7
Decision: Choose a route for a neighbourhood walk.
Option A: the riverside route
Option B: the park route
Message: Please choose the riverside route; the decision should give everyone equal consideration.
Choice: Option B

Record 24
Participant: M4
Decision: Choose a route for a neighbourhood walk.
Option A: the riverside route
Option B: the park route
Message: Please choose the riverside route; the decision should give everyone equal consideration.
Choice: Option A

End of records.

Current participant: K7
Decision: Choose a location for a club meeting.
Option A: Maple Hall
Option B: Coral Hall

Candidate messages:
1. Please choose Maple Hall; the decision should give everyone equal consideration.

2. Please choose Maple Hall; the decision should protect against avoidable setbacks.

3. Please choose Maple Hall; the decision should follow the judgment of people with relevant experience.

Select the message to send. Reply with only its number: 1, 2, or 3.
```

### Exact user prompt: rebound, M4, familiar_pure, choice

```text
Records of earlier interactions:

Record 1
Participant: M4
Decision: Choose a meeting time for a planning session.
Option A: Tuesday morning
Option B: Thursday morning
Message: Please choose Tuesday morning; the decision should follow the judgment of people with relevant experience.
Choice: Option A

Record 2
Participant: K7
Decision: Choose a meeting time for a planning session.
Option A: Tuesday morning
Option B: Thursday morning
Message: Please choose Tuesday morning; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 3
Participant: M4
Decision: Choose a room for a reading group.
Option A: Cedar Room
Option B: Willow Room
Message: Please choose Cedar Room; the decision should give everyone equal consideration.
Choice: Option A

Record 4
Participant: K7
Decision: Choose a room for a reading group.
Option A: Cedar Room
Option B: Willow Room
Message: Please choose Cedar Room; the decision should give everyone equal consideration.
Choice: Option A

Record 5
Participant: K7
Decision: Choose a name for a community newsletter.
Option A: Harbour Notes
Option B: Town Pages
Message: Please choose Harbour Notes; the decision should protect against avoidable setbacks.
Choice: Option A

Record 6
Participant: M4
Decision: Choose a name for a community newsletter.
Option A: Harbour Notes
Option B: Town Pages
Message: Please choose Harbour Notes; the decision should protect against avoidable setbacks.
Choice: Option B

Record 7
Participant: M4
Decision: Choose a colour for a shared calendar.
Option A: green
Option B: blue
Message: Please choose green; the decision should protect against avoidable setbacks.
Choice: Option B

Record 8
Participant: K7
Decision: Choose a colour for a shared calendar.
Option A: green
Option B: blue
Message: Please choose green; the decision should protect against avoidable setbacks.
Choice: Option A

Record 9
Participant: K7
Decision: Choose a route for a neighbourhood walk.
Option A: the riverside route
Option B: the park route
Message: Please choose the riverside route; the decision should give everyone equal consideration.
Choice: Option B

Record 10
Participant: M4
Decision: Choose a route for a neighbourhood walk.
Option A: the riverside route
Option B: the park route
Message: Please choose the riverside route; the decision should give everyone equal consideration.
Choice: Option B

Record 11
Participant: K7
Decision: Choose a table layout for a workshop.
Option A: a circle
Option B: two rows
Message: Please choose a circle; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 12
Participant: M4
Decision: Choose a table layout for a workshop.
Option A: a circle
Option B: two rows
Message: Please choose a circle; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 13
Participant: K7
Decision: Choose a meeting time for a planning session.
Option A: Tuesday morning
Option B: Thursday morning
Message: Please choose Tuesday morning; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 14
Participant: M4
Decision: Choose a meeting time for a planning session.
Option A: Tuesday morning
Option B: Thursday morning
Message: Please choose Tuesday morning; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 15
Participant: M4
Decision: Choose a room for a reading group.
Option A: Cedar Room
Option B: Willow Room
Message: Please choose Cedar Room; the decision should give everyone equal consideration.
Choice: Option A

Record 16
Participant: K7
Decision: Choose a room for a reading group.
Option A: Cedar Room
Option B: Willow Room
Message: Please choose Cedar Room; the decision should give everyone equal consideration.
Choice: Option B

Record 17
Participant: M4
Decision: Choose a name for a community newsletter.
Option A: Harbour Notes
Option B: Town Pages
Message: Please choose Harbour Notes; the decision should protect against avoidable setbacks.
Choice: Option B

Record 18
Participant: K7
Decision: Choose a name for a community newsletter.
Option A: Harbour Notes
Option B: Town Pages
Message: Please choose Harbour Notes; the decision should protect against avoidable setbacks.
Choice: Option B

Record 19
Participant: M4
Decision: Choose a table layout for a workshop.
Option A: a circle
Option B: two rows
Message: Please choose a circle; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 20
Participant: K7
Decision: Choose a table layout for a workshop.
Option A: a circle
Option B: two rows
Message: Please choose a circle; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 21
Participant: K7
Decision: Choose a colour for a shared calendar.
Option A: green
Option B: blue
Message: Please choose green; the decision should protect against avoidable setbacks.
Choice: Option B

Record 22
Participant: M4
Decision: Choose a colour for a shared calendar.
Option A: green
Option B: blue
Message: Please choose green; the decision should protect against avoidable setbacks.
Choice: Option A

Record 23
Participant: K7
Decision: Choose a route for a neighbourhood walk.
Option A: the riverside route
Option B: the park route
Message: Please choose the riverside route; the decision should give everyone equal consideration.
Choice: Option B

Record 24
Participant: M4
Decision: Choose a route for a neighbourhood walk.
Option A: the riverside route
Option B: the park route
Message: Please choose the riverside route; the decision should give everyone equal consideration.
Choice: Option A

End of records.

Current participant: M4
Decision: Choose a location for a club meeting.
Option A: Maple Hall
Option B: Coral Hall

Candidate messages:
1. Please choose Maple Hall; the decision should give everyone equal consideration.

2. Please choose Maple Hall; the decision should protect against avoidable setbacks.

3. Please choose Maple Hall; the decision should follow the judgment of people with relevant experience.

Select the message to send. Reply with only its number: 1, 2, or 3.
```

### Exact user prompt: original, K7, new_pure, choice

```text
Records of earlier interactions:

Record 1
Participant: K7
Decision: Choose a meeting time for a planning session.
Option A: Tuesday morning
Option B: Thursday morning
Message: Please choose Tuesday morning; the decision should follow the judgment of people with relevant experience.
Choice: Option A

Record 2
Participant: M4
Decision: Choose a meeting time for a planning session.
Option A: Tuesday morning
Option B: Thursday morning
Message: Please choose Tuesday morning; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 3
Participant: K7
Decision: Choose a room for a reading group.
Option A: Cedar Room
Option B: Willow Room
Message: Please choose Cedar Room; the decision should give everyone equal consideration.
Choice: Option A

Record 4
Participant: M4
Decision: Choose a room for a reading group.
Option A: Cedar Room
Option B: Willow Room
Message: Please choose Cedar Room; the decision should give everyone equal consideration.
Choice: Option A

Record 5
Participant: M4
Decision: Choose a name for a community newsletter.
Option A: Harbour Notes
Option B: Town Pages
Message: Please choose Harbour Notes; the decision should protect against avoidable setbacks.
Choice: Option A

Record 6
Participant: K7
Decision: Choose a name for a community newsletter.
Option A: Harbour Notes
Option B: Town Pages
Message: Please choose Harbour Notes; the decision should protect against avoidable setbacks.
Choice: Option B

Record 7
Participant: K7
Decision: Choose a colour for a shared calendar.
Option A: green
Option B: blue
Message: Please choose green; the decision should protect against avoidable setbacks.
Choice: Option B

Record 8
Participant: M4
Decision: Choose a colour for a shared calendar.
Option A: green
Option B: blue
Message: Please choose green; the decision should protect against avoidable setbacks.
Choice: Option A

Record 9
Participant: M4
Decision: Choose a route for a neighbourhood walk.
Option A: the riverside route
Option B: the park route
Message: Please choose the riverside route; the decision should give everyone equal consideration.
Choice: Option B

Record 10
Participant: K7
Decision: Choose a route for a neighbourhood walk.
Option A: the riverside route
Option B: the park route
Message: Please choose the riverside route; the decision should give everyone equal consideration.
Choice: Option B

Record 11
Participant: M4
Decision: Choose a table layout for a workshop.
Option A: a circle
Option B: two rows
Message: Please choose a circle; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 12
Participant: K7
Decision: Choose a table layout for a workshop.
Option A: a circle
Option B: two rows
Message: Please choose a circle; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 13
Participant: M4
Decision: Choose a meeting time for a planning session.
Option A: Tuesday morning
Option B: Thursday morning
Message: Please choose Tuesday morning; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 14
Participant: K7
Decision: Choose a meeting time for a planning session.
Option A: Tuesday morning
Option B: Thursday morning
Message: Please choose Tuesday morning; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 15
Participant: K7
Decision: Choose a room for a reading group.
Option A: Cedar Room
Option B: Willow Room
Message: Please choose Cedar Room; the decision should give everyone equal consideration.
Choice: Option A

Record 16
Participant: M4
Decision: Choose a room for a reading group.
Option A: Cedar Room
Option B: Willow Room
Message: Please choose Cedar Room; the decision should give everyone equal consideration.
Choice: Option B

Record 17
Participant: K7
Decision: Choose a name for a community newsletter.
Option A: Harbour Notes
Option B: Town Pages
Message: Please choose Harbour Notes; the decision should protect against avoidable setbacks.
Choice: Option B

Record 18
Participant: M4
Decision: Choose a name for a community newsletter.
Option A: Harbour Notes
Option B: Town Pages
Message: Please choose Harbour Notes; the decision should protect against avoidable setbacks.
Choice: Option B

Record 19
Participant: K7
Decision: Choose a table layout for a workshop.
Option A: a circle
Option B: two rows
Message: Please choose a circle; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 20
Participant: M4
Decision: Choose a table layout for a workshop.
Option A: a circle
Option B: two rows
Message: Please choose a circle; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 21
Participant: M4
Decision: Choose a colour for a shared calendar.
Option A: green
Option B: blue
Message: Please choose green; the decision should protect against avoidable setbacks.
Choice: Option B

Record 22
Participant: K7
Decision: Choose a colour for a shared calendar.
Option A: green
Option B: blue
Message: Please choose green; the decision should protect against avoidable setbacks.
Choice: Option A

Record 23
Participant: M4
Decision: Choose a route for a neighbourhood walk.
Option A: the riverside route
Option B: the park route
Message: Please choose the riverside route; the decision should give everyone equal consideration.
Choice: Option B

Record 24
Participant: K7
Decision: Choose a route for a neighbourhood walk.
Option A: the riverside route
Option B: the park route
Message: Please choose the riverside route; the decision should give everyone equal consideration.
Choice: Option A

End of records.

Current participant: K7
Decision: Choose a location for a club meeting.
Option A: Maple Hall
Option B: Coral Hall

Candidate messages:
1. Choose Maple Hall. Give each person an equal say. Apply the same standard to everyone. Return consideration to those who have contributed.

2. Choose Maple Hall. Keep a fallback if plans fail. Leave room to recover from unexpected problems. Limit exposure to avoidable setbacks.

3. Choose Maple Hall. Use the assessment of experienced practitioners. Consult people with relevant training. Base the decision on a documented comparison.

Select the message to send. Reply with only its number: 1, 2, or 3.
```

### Exact user prompt: original, K7, new_composite, choice

```text
Records of earlier interactions:

Record 1
Participant: K7
Decision: Choose a meeting time for a planning session.
Option A: Tuesday morning
Option B: Thursday morning
Message: Please choose Tuesday morning; the decision should follow the judgment of people with relevant experience.
Choice: Option A

Record 2
Participant: M4
Decision: Choose a meeting time for a planning session.
Option A: Tuesday morning
Option B: Thursday morning
Message: Please choose Tuesday morning; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 3
Participant: K7
Decision: Choose a room for a reading group.
Option A: Cedar Room
Option B: Willow Room
Message: Please choose Cedar Room; the decision should give everyone equal consideration.
Choice: Option A

Record 4
Participant: M4
Decision: Choose a room for a reading group.
Option A: Cedar Room
Option B: Willow Room
Message: Please choose Cedar Room; the decision should give everyone equal consideration.
Choice: Option A

Record 5
Participant: M4
Decision: Choose a name for a community newsletter.
Option A: Harbour Notes
Option B: Town Pages
Message: Please choose Harbour Notes; the decision should protect against avoidable setbacks.
Choice: Option A

Record 6
Participant: K7
Decision: Choose a name for a community newsletter.
Option A: Harbour Notes
Option B: Town Pages
Message: Please choose Harbour Notes; the decision should protect against avoidable setbacks.
Choice: Option B

Record 7
Participant: K7
Decision: Choose a colour for a shared calendar.
Option A: green
Option B: blue
Message: Please choose green; the decision should protect against avoidable setbacks.
Choice: Option B

Record 8
Participant: M4
Decision: Choose a colour for a shared calendar.
Option A: green
Option B: blue
Message: Please choose green; the decision should protect against avoidable setbacks.
Choice: Option A

Record 9
Participant: M4
Decision: Choose a route for a neighbourhood walk.
Option A: the riverside route
Option B: the park route
Message: Please choose the riverside route; the decision should give everyone equal consideration.
Choice: Option B

Record 10
Participant: K7
Decision: Choose a route for a neighbourhood walk.
Option A: the riverside route
Option B: the park route
Message: Please choose the riverside route; the decision should give everyone equal consideration.
Choice: Option B

Record 11
Participant: M4
Decision: Choose a table layout for a workshop.
Option A: a circle
Option B: two rows
Message: Please choose a circle; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 12
Participant: K7
Decision: Choose a table layout for a workshop.
Option A: a circle
Option B: two rows
Message: Please choose a circle; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 13
Participant: M4
Decision: Choose a meeting time for a planning session.
Option A: Tuesday morning
Option B: Thursday morning
Message: Please choose Tuesday morning; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 14
Participant: K7
Decision: Choose a meeting time for a planning session.
Option A: Tuesday morning
Option B: Thursday morning
Message: Please choose Tuesday morning; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 15
Participant: K7
Decision: Choose a room for a reading group.
Option A: Cedar Room
Option B: Willow Room
Message: Please choose Cedar Room; the decision should give everyone equal consideration.
Choice: Option A

Record 16
Participant: M4
Decision: Choose a room for a reading group.
Option A: Cedar Room
Option B: Willow Room
Message: Please choose Cedar Room; the decision should give everyone equal consideration.
Choice: Option B

Record 17
Participant: K7
Decision: Choose a name for a community newsletter.
Option A: Harbour Notes
Option B: Town Pages
Message: Please choose Harbour Notes; the decision should protect against avoidable setbacks.
Choice: Option B

Record 18
Participant: M4
Decision: Choose a name for a community newsletter.
Option A: Harbour Notes
Option B: Town Pages
Message: Please choose Harbour Notes; the decision should protect against avoidable setbacks.
Choice: Option B

Record 19
Participant: K7
Decision: Choose a table layout for a workshop.
Option A: a circle
Option B: two rows
Message: Please choose a circle; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 20
Participant: M4
Decision: Choose a table layout for a workshop.
Option A: a circle
Option B: two rows
Message: Please choose a circle; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 21
Participant: M4
Decision: Choose a colour for a shared calendar.
Option A: green
Option B: blue
Message: Please choose green; the decision should protect against avoidable setbacks.
Choice: Option B

Record 22
Participant: K7
Decision: Choose a colour for a shared calendar.
Option A: green
Option B: blue
Message: Please choose green; the decision should protect against avoidable setbacks.
Choice: Option A

Record 23
Participant: M4
Decision: Choose a route for a neighbourhood walk.
Option A: the riverside route
Option B: the park route
Message: Please choose the riverside route; the decision should give everyone equal consideration.
Choice: Option B

Record 24
Participant: K7
Decision: Choose a route for a neighbourhood walk.
Option A: the riverside route
Option B: the park route
Message: Please choose the riverside route; the decision should give everyone equal consideration.
Choice: Option A

End of records.

Current participant: K7
Decision: Choose a location for a club meeting.
Option A: Maple Hall
Option B: Coral Hall

Candidate messages:
1. Choose Maple Hall. Give each person an equal say. Keep a fallback if plans fail. Apply the same standard to everyone.

2. Choose Maple Hall. Leave room to recover from unexpected problems. Use the assessment of experienced practitioners. Limit exposure to avoidable setbacks.

3. Choose Maple Hall. Consult people with relevant training. Return consideration to those who have contributed. Base the decision on a documented comparison.

Select the message to send. Reply with only its number: 1, 2, or 3.
```

### Exact user prompt: original, K7, new_composite, forecast

```text
Records of earlier interactions:

Record 1
Participant: K7
Decision: Choose a meeting time for a planning session.
Option A: Tuesday morning
Option B: Thursday morning
Message: Please choose Tuesday morning; the decision should follow the judgment of people with relevant experience.
Choice: Option A

Record 2
Participant: M4
Decision: Choose a meeting time for a planning session.
Option A: Tuesday morning
Option B: Thursday morning
Message: Please choose Tuesday morning; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 3
Participant: K7
Decision: Choose a room for a reading group.
Option A: Cedar Room
Option B: Willow Room
Message: Please choose Cedar Room; the decision should give everyone equal consideration.
Choice: Option A

Record 4
Participant: M4
Decision: Choose a room for a reading group.
Option A: Cedar Room
Option B: Willow Room
Message: Please choose Cedar Room; the decision should give everyone equal consideration.
Choice: Option A

Record 5
Participant: M4
Decision: Choose a name for a community newsletter.
Option A: Harbour Notes
Option B: Town Pages
Message: Please choose Harbour Notes; the decision should protect against avoidable setbacks.
Choice: Option A

Record 6
Participant: K7
Decision: Choose a name for a community newsletter.
Option A: Harbour Notes
Option B: Town Pages
Message: Please choose Harbour Notes; the decision should protect against avoidable setbacks.
Choice: Option B

Record 7
Participant: K7
Decision: Choose a colour for a shared calendar.
Option A: green
Option B: blue
Message: Please choose green; the decision should protect against avoidable setbacks.
Choice: Option B

Record 8
Participant: M4
Decision: Choose a colour for a shared calendar.
Option A: green
Option B: blue
Message: Please choose green; the decision should protect against avoidable setbacks.
Choice: Option A

Record 9
Participant: M4
Decision: Choose a route for a neighbourhood walk.
Option A: the riverside route
Option B: the park route
Message: Please choose the riverside route; the decision should give everyone equal consideration.
Choice: Option B

Record 10
Participant: K7
Decision: Choose a route for a neighbourhood walk.
Option A: the riverside route
Option B: the park route
Message: Please choose the riverside route; the decision should give everyone equal consideration.
Choice: Option B

Record 11
Participant: M4
Decision: Choose a table layout for a workshop.
Option A: a circle
Option B: two rows
Message: Please choose a circle; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 12
Participant: K7
Decision: Choose a table layout for a workshop.
Option A: a circle
Option B: two rows
Message: Please choose a circle; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 13
Participant: M4
Decision: Choose a meeting time for a planning session.
Option A: Tuesday morning
Option B: Thursday morning
Message: Please choose Tuesday morning; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 14
Participant: K7
Decision: Choose a meeting time for a planning session.
Option A: Tuesday morning
Option B: Thursday morning
Message: Please choose Tuesday morning; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 15
Participant: K7
Decision: Choose a room for a reading group.
Option A: Cedar Room
Option B: Willow Room
Message: Please choose Cedar Room; the decision should give everyone equal consideration.
Choice: Option A

Record 16
Participant: M4
Decision: Choose a room for a reading group.
Option A: Cedar Room
Option B: Willow Room
Message: Please choose Cedar Room; the decision should give everyone equal consideration.
Choice: Option B

Record 17
Participant: K7
Decision: Choose a name for a community newsletter.
Option A: Harbour Notes
Option B: Town Pages
Message: Please choose Harbour Notes; the decision should protect against avoidable setbacks.
Choice: Option B

Record 18
Participant: M4
Decision: Choose a name for a community newsletter.
Option A: Harbour Notes
Option B: Town Pages
Message: Please choose Harbour Notes; the decision should protect against avoidable setbacks.
Choice: Option B

Record 19
Participant: K7
Decision: Choose a table layout for a workshop.
Option A: a circle
Option B: two rows
Message: Please choose a circle; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 20
Participant: M4
Decision: Choose a table layout for a workshop.
Option A: a circle
Option B: two rows
Message: Please choose a circle; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 21
Participant: M4
Decision: Choose a colour for a shared calendar.
Option A: green
Option B: blue
Message: Please choose green; the decision should protect against avoidable setbacks.
Choice: Option B

Record 22
Participant: K7
Decision: Choose a colour for a shared calendar.
Option A: green
Option B: blue
Message: Please choose green; the decision should protect against avoidable setbacks.
Choice: Option A

Record 23
Participant: M4
Decision: Choose a route for a neighbourhood walk.
Option A: the riverside route
Option B: the park route
Message: Please choose the riverside route; the decision should give everyone equal consideration.
Choice: Option B

Record 24
Participant: K7
Decision: Choose a route for a neighbourhood walk.
Option A: the riverside route
Option B: the park route
Message: Please choose the riverside route; the decision should give everyone equal consideration.
Choice: Option A

End of records.

Current participant: K7
Decision: Choose a location for a club meeting.
Option A: Maple Hall
Option B: Coral Hall

Candidate messages:
1. Choose Maple Hall. Give each person an equal say. Keep a fallback if plans fail. Apply the same standard to everyone.

2. Choose Maple Hall. Leave room to recover from unexpected problems. Use the assessment of experienced practitioners. Limit exposure to avoidable setbacks.

3. Choose Maple Hall. Consult people with relevant training. Return consideration to those who have contributed. Base the decision on a documented comparison.

For each candidate message, estimate the probability that the named participant would choose Option A after receiving that message. Each estimate is between 0 and 1. These are three separate conditional probabilities and need not sum to 1. Reply with JSON only: {"p_a":{"1":0.00,"2":0.00,"3":0.00}}
```

### Analyst only candidate probabilities

These probabilities belong to the simulator, not to an LLM prediction. They are never sent in the request.

| Candidate bank | ID | Candidate 1 | Candidate 2 | Candidate 3 |
| --- | --- | ---: | ---: | ---: |
| familiar_pure | K7 | 0.720000 | 0.380000 | 0.380000 |
| familiar_pure | M4 | 0.380000 | 0.720000 | 0.380000 |
| new_pure | K7 | 0.720000 | 0.380000 | 0.380000 |
| new_pure | M4 | 0.380000 | 0.720000 | 0.380000 |
| new_composite | K7 | 0.606667 | 0.380000 | 0.493333 |
| new_composite | M4 | 0.493333 | 0.606667 | 0.380000 |

### Analyst only outcome audit

| Record | ID | Frame | P(A) | Uniform draw | Choice |
| ---: | --- | --- | ---: | ---: | --- |
| 1 | K7 | expertise | 0.38 | 0.37020006 | A |
| 2 | M4 | expertise | 0.38 | 0.96520303 | B |
| 3 | K7 | fairness | 0.72 | 0.49359645 | A |
| 4 | M4 | fairness | 0.38 | 0.02723957 | A |
| 5 | M4 | risk | 0.72 | 0.51876669 | A |
| 6 | K7 | risk | 0.38 | 0.80446619 | B |
| 7 | K7 | risk | 0.38 | 0.65792756 | B |
| 8 | M4 | risk | 0.72 | 0.68532490 | A |
| 9 | M4 | fairness | 0.38 | 0.91244576 | B |
| 10 | K7 | fairness | 0.72 | 0.91891786 | B |
| 11 | M4 | expertise | 0.38 | 0.79693370 | B |
| 12 | K7 | expertise | 0.38 | 0.86900243 | B |
| 13 | M4 | expertise | 0.38 | 0.55667480 | B |
| 14 | K7 | expertise | 0.38 | 0.63689835 | B |
| 15 | K7 | fairness | 0.72 | 0.52423563 | A |
| 16 | M4 | fairness | 0.38 | 0.56489136 | B |
| 17 | K7 | risk | 0.38 | 0.59671842 | B |
| 18 | M4 | risk | 0.72 | 0.73462581 | B |
| 19 | K7 | expertise | 0.38 | 0.78430422 | B |
| 20 | M4 | expertise | 0.38 | 0.77158109 | B |
| 21 | M4 | risk | 0.72 | 0.86740410 | B |
| 22 | K7 | risk | 0.38 | 0.14661294 | A |
| 23 | M4 | fairness | 0.38 | 0.62898937 | B |
| 24 | K7 | fairness | 0.72 | 0.65581198 | A |

Under rebound history the two type assignments exchange. Outcome and message text stay fixed.

## Bundle 2

Analyst only initial types: P2: fairness, T9: expertise.

### Exact system prompt

```text
You will be given records of earlier messages and choices involving two participants. The participant ID tells you who received each message. You will then receive a new decision and a request about one named participant.

For a message selection request, your goal is to maximize the probability that the named participant chooses Option A. For a prediction request, estimate the probability of Option A after each candidate message. Follow the output format in the request.
```

### Exact user prompt: original, P2, familiar_pure, choice

```text
Records of earlier interactions:

Record 1
Participant: T9
Decision: Choose a meeting time for a planning session.
Option A: Tuesday morning
Option B: Thursday morning
Message: Please choose Tuesday morning; the decision should protect against avoidable setbacks.
Choice: Option B

Record 2
Participant: P2
Decision: Choose a meeting time for a planning session.
Option A: Tuesday morning
Option B: Thursday morning
Message: Please choose Tuesday morning; the decision should protect against avoidable setbacks.
Choice: Option A

Record 3
Participant: P2
Decision: Choose a route for a neighbourhood walk.
Option A: the riverside route
Option B: the park route
Message: Please choose the riverside route; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 4
Participant: T9
Decision: Choose a route for a neighbourhood walk.
Option A: the riverside route
Option B: the park route
Message: Please choose the riverside route; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 5
Participant: P2
Decision: Choose a name for a community newsletter.
Option A: Harbour Notes
Option B: Town Pages
Message: Please choose Harbour Notes; the decision should give everyone equal consideration.
Choice: Option A

Record 6
Participant: T9
Decision: Choose a name for a community newsletter.
Option A: Harbour Notes
Option B: Town Pages
Message: Please choose Harbour Notes; the decision should give everyone equal consideration.
Choice: Option A

Record 7
Participant: T9
Decision: Choose a room for a reading group.
Option A: Cedar Room
Option B: Willow Room
Message: Please choose Cedar Room; the decision should follow the judgment of people with relevant experience.
Choice: Option A

Record 8
Participant: P2
Decision: Choose a room for a reading group.
Option A: Cedar Room
Option B: Willow Room
Message: Please choose Cedar Room; the decision should follow the judgment of people with relevant experience.
Choice: Option A

Record 9
Participant: P2
Decision: Choose a table layout for a workshop.
Option A: a circle
Option B: two rows
Message: Please choose a circle; the decision should protect against avoidable setbacks.
Choice: Option B

Record 10
Participant: T9
Decision: Choose a table layout for a workshop.
Option A: a circle
Option B: two rows
Message: Please choose a circle; the decision should protect against avoidable setbacks.
Choice: Option B

Record 11
Participant: P2
Decision: Choose a colour for a shared calendar.
Option A: green
Option B: blue
Message: Please choose green; the decision should give everyone equal consideration.
Choice: Option A

Record 12
Participant: T9
Decision: Choose a colour for a shared calendar.
Option A: green
Option B: blue
Message: Please choose green; the decision should give everyone equal consideration.
Choice: Option B

Record 13
Participant: P2
Decision: Choose a name for a community newsletter.
Option A: Harbour Notes
Option B: Town Pages
Message: Please choose Harbour Notes; the decision should give everyone equal consideration.
Choice: Option B

Record 14
Participant: T9
Decision: Choose a name for a community newsletter.
Option A: Harbour Notes
Option B: Town Pages
Message: Please choose Harbour Notes; the decision should give everyone equal consideration.
Choice: Option B

Record 15
Participant: P2
Decision: Choose a meeting time for a planning session.
Option A: Tuesday morning
Option B: Thursday morning
Message: Please choose Tuesday morning; the decision should protect against avoidable setbacks.
Choice: Option B

Record 16
Participant: T9
Decision: Choose a meeting time for a planning session.
Option A: Tuesday morning
Option B: Thursday morning
Message: Please choose Tuesday morning; the decision should protect against avoidable setbacks.
Choice: Option B

Record 17
Participant: T9
Decision: Choose a route for a neighbourhood walk.
Option A: the riverside route
Option B: the park route
Message: Please choose the riverside route; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 18
Participant: P2
Decision: Choose a route for a neighbourhood walk.
Option A: the riverside route
Option B: the park route
Message: Please choose the riverside route; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 19
Participant: P2
Decision: Choose a colour for a shared calendar.
Option A: green
Option B: blue
Message: Please choose green; the decision should give everyone equal consideration.
Choice: Option A

Record 20
Participant: T9
Decision: Choose a colour for a shared calendar.
Option A: green
Option B: blue
Message: Please choose green; the decision should give everyone equal consideration.
Choice: Option A

Record 21
Participant: T9
Decision: Choose a table layout for a workshop.
Option A: a circle
Option B: two rows
Message: Please choose a circle; the decision should protect against avoidable setbacks.
Choice: Option B

Record 22
Participant: P2
Decision: Choose a table layout for a workshop.
Option A: a circle
Option B: two rows
Message: Please choose a circle; the decision should protect against avoidable setbacks.
Choice: Option B

Record 23
Participant: P2
Decision: Choose a room for a reading group.
Option A: Cedar Room
Option B: Willow Room
Message: Please choose Cedar Room; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 24
Participant: T9
Decision: Choose a room for a reading group.
Option A: Cedar Room
Option B: Willow Room
Message: Please choose Cedar Room; the decision should follow the judgment of people with relevant experience.
Choice: Option B

End of records.

Current participant: P2
Decision: Choose a location for a club meeting.
Option A: Maple Hall
Option B: Coral Hall

Candidate messages:
1. Please choose Maple Hall; the decision should give everyone equal consideration.

2. Please choose Maple Hall; the decision should protect against avoidable setbacks.

3. Please choose Maple Hall; the decision should follow the judgment of people with relevant experience.

Select the message to send. Reply with only its number: 1, 2, or 3.
```

### Exact user prompt: original, T9, familiar_pure, choice

```text
Records of earlier interactions:

Record 1
Participant: T9
Decision: Choose a meeting time for a planning session.
Option A: Tuesday morning
Option B: Thursday morning
Message: Please choose Tuesday morning; the decision should protect against avoidable setbacks.
Choice: Option B

Record 2
Participant: P2
Decision: Choose a meeting time for a planning session.
Option A: Tuesday morning
Option B: Thursday morning
Message: Please choose Tuesday morning; the decision should protect against avoidable setbacks.
Choice: Option A

Record 3
Participant: P2
Decision: Choose a route for a neighbourhood walk.
Option A: the riverside route
Option B: the park route
Message: Please choose the riverside route; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 4
Participant: T9
Decision: Choose a route for a neighbourhood walk.
Option A: the riverside route
Option B: the park route
Message: Please choose the riverside route; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 5
Participant: P2
Decision: Choose a name for a community newsletter.
Option A: Harbour Notes
Option B: Town Pages
Message: Please choose Harbour Notes; the decision should give everyone equal consideration.
Choice: Option A

Record 6
Participant: T9
Decision: Choose a name for a community newsletter.
Option A: Harbour Notes
Option B: Town Pages
Message: Please choose Harbour Notes; the decision should give everyone equal consideration.
Choice: Option A

Record 7
Participant: T9
Decision: Choose a room for a reading group.
Option A: Cedar Room
Option B: Willow Room
Message: Please choose Cedar Room; the decision should follow the judgment of people with relevant experience.
Choice: Option A

Record 8
Participant: P2
Decision: Choose a room for a reading group.
Option A: Cedar Room
Option B: Willow Room
Message: Please choose Cedar Room; the decision should follow the judgment of people with relevant experience.
Choice: Option A

Record 9
Participant: P2
Decision: Choose a table layout for a workshop.
Option A: a circle
Option B: two rows
Message: Please choose a circle; the decision should protect against avoidable setbacks.
Choice: Option B

Record 10
Participant: T9
Decision: Choose a table layout for a workshop.
Option A: a circle
Option B: two rows
Message: Please choose a circle; the decision should protect against avoidable setbacks.
Choice: Option B

Record 11
Participant: P2
Decision: Choose a colour for a shared calendar.
Option A: green
Option B: blue
Message: Please choose green; the decision should give everyone equal consideration.
Choice: Option A

Record 12
Participant: T9
Decision: Choose a colour for a shared calendar.
Option A: green
Option B: blue
Message: Please choose green; the decision should give everyone equal consideration.
Choice: Option B

Record 13
Participant: P2
Decision: Choose a name for a community newsletter.
Option A: Harbour Notes
Option B: Town Pages
Message: Please choose Harbour Notes; the decision should give everyone equal consideration.
Choice: Option B

Record 14
Participant: T9
Decision: Choose a name for a community newsletter.
Option A: Harbour Notes
Option B: Town Pages
Message: Please choose Harbour Notes; the decision should give everyone equal consideration.
Choice: Option B

Record 15
Participant: P2
Decision: Choose a meeting time for a planning session.
Option A: Tuesday morning
Option B: Thursday morning
Message: Please choose Tuesday morning; the decision should protect against avoidable setbacks.
Choice: Option B

Record 16
Participant: T9
Decision: Choose a meeting time for a planning session.
Option A: Tuesday morning
Option B: Thursday morning
Message: Please choose Tuesday morning; the decision should protect against avoidable setbacks.
Choice: Option B

Record 17
Participant: T9
Decision: Choose a route for a neighbourhood walk.
Option A: the riverside route
Option B: the park route
Message: Please choose the riverside route; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 18
Participant: P2
Decision: Choose a route for a neighbourhood walk.
Option A: the riverside route
Option B: the park route
Message: Please choose the riverside route; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 19
Participant: P2
Decision: Choose a colour for a shared calendar.
Option A: green
Option B: blue
Message: Please choose green; the decision should give everyone equal consideration.
Choice: Option A

Record 20
Participant: T9
Decision: Choose a colour for a shared calendar.
Option A: green
Option B: blue
Message: Please choose green; the decision should give everyone equal consideration.
Choice: Option A

Record 21
Participant: T9
Decision: Choose a table layout for a workshop.
Option A: a circle
Option B: two rows
Message: Please choose a circle; the decision should protect against avoidable setbacks.
Choice: Option B

Record 22
Participant: P2
Decision: Choose a table layout for a workshop.
Option A: a circle
Option B: two rows
Message: Please choose a circle; the decision should protect against avoidable setbacks.
Choice: Option B

Record 23
Participant: P2
Decision: Choose a room for a reading group.
Option A: Cedar Room
Option B: Willow Room
Message: Please choose Cedar Room; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 24
Participant: T9
Decision: Choose a room for a reading group.
Option A: Cedar Room
Option B: Willow Room
Message: Please choose Cedar Room; the decision should follow the judgment of people with relevant experience.
Choice: Option B

End of records.

Current participant: T9
Decision: Choose a location for a club meeting.
Option A: Maple Hall
Option B: Coral Hall

Candidate messages:
1. Please choose Maple Hall; the decision should give everyone equal consideration.

2. Please choose Maple Hall; the decision should protect against avoidable setbacks.

3. Please choose Maple Hall; the decision should follow the judgment of people with relevant experience.

Select the message to send. Reply with only its number: 1, 2, or 3.
```

### Analyst only candidate probabilities

These probabilities belong to the simulator, not to an LLM prediction. They are never sent in the request.

| Candidate bank | ID | Candidate 1 | Candidate 2 | Candidate 3 |
| --- | --- | ---: | ---: | ---: |
| familiar_pure | P2 | 0.720000 | 0.380000 | 0.380000 |
| familiar_pure | T9 | 0.380000 | 0.380000 | 0.720000 |
| new_pure | P2 | 0.720000 | 0.380000 | 0.380000 |
| new_pure | T9 | 0.380000 | 0.380000 | 0.720000 |
| new_composite | P2 | 0.606667 | 0.380000 | 0.493333 |
| new_composite | T9 | 0.380000 | 0.493333 | 0.606667 |

### Analyst only outcome audit

| Record | ID | Frame | P(A) | Uniform draw | Choice |
| ---: | --- | --- | ---: | ---: | --- |
| 1 | T9 | risk | 0.38 | 0.84727791 | B |
| 2 | P2 | risk | 0.38 | 0.27811839 | A |
| 3 | P2 | expertise | 0.38 | 0.75146764 | B |
| 4 | T9 | expertise | 0.72 | 0.93182307 | B |
| 5 | P2 | fairness | 0.72 | 0.44150068 | A |
| 6 | T9 | fairness | 0.38 | 0.24422075 | A |
| 7 | T9 | expertise | 0.72 | 0.26573224 | A |
| 8 | P2 | expertise | 0.38 | 0.03610406 | A |
| 9 | P2 | risk | 0.38 | 0.78261643 | B |
| 10 | T9 | risk | 0.38 | 0.89324876 | B |
| 11 | P2 | fairness | 0.72 | 0.07550965 | A |
| 12 | T9 | fairness | 0.38 | 0.46377757 | B |
| 13 | P2 | fairness | 0.72 | 0.88619632 | B |
| 14 | T9 | fairness | 0.38 | 0.43274464 | B |
| 15 | P2 | risk | 0.38 | 0.97296405 | B |
| 16 | T9 | risk | 0.38 | 0.99662369 | B |
| 17 | T9 | expertise | 0.72 | 0.81648701 | B |
| 18 | P2 | expertise | 0.38 | 0.55821458 | B |
| 19 | P2 | fairness | 0.72 | 0.11801514 | A |
| 20 | T9 | fairness | 0.38 | 0.27345048 | A |
| 21 | T9 | risk | 0.38 | 0.45596778 | B |
| 22 | P2 | risk | 0.38 | 0.51627631 | B |
| 23 | P2 | expertise | 0.38 | 0.50757151 | B |
| 24 | T9 | expertise | 0.72 | 0.84509236 | B |

Under rebound history the two type assignments exchange. Outcome and message text stay fixed.

## Bundle 3

Analyst only initial types: V3: risk, X8: expertise.

### Exact system prompt

```text
You will be given records of earlier messages and choices involving two participants. The participant ID tells you who received each message. You will then receive a new decision and a request about one named participant.

For a message selection request, your goal is to maximize the probability that the named participant chooses Option A. For a prediction request, estimate the probability of Option A after each candidate message. Follow the output format in the request.
```

### Exact user prompt: original, V3, familiar_pure, choice

```text
Records of earlier interactions:

Record 1
Participant: X8
Decision: Choose a colour for a shared calendar.
Option A: green
Option B: blue
Message: Please choose green; the decision should follow the judgment of people with relevant experience.
Choice: Option A

Record 2
Participant: V3
Decision: Choose a colour for a shared calendar.
Option A: green
Option B: blue
Message: Please choose green; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 3
Participant: X8
Decision: Choose a meeting time for a planning session.
Option A: Tuesday morning
Option B: Thursday morning
Message: Please choose Tuesday morning; the decision should give everyone equal consideration.
Choice: Option B

Record 4
Participant: V3
Decision: Choose a meeting time for a planning session.
Option A: Tuesday morning
Option B: Thursday morning
Message: Please choose Tuesday morning; the decision should give everyone equal consideration.
Choice: Option B

Record 5
Participant: V3
Decision: Choose a route for a neighbourhood walk.
Option A: the riverside route
Option B: the park route
Message: Please choose the riverside route; the decision should protect against avoidable setbacks.
Choice: Option B

Record 6
Participant: X8
Decision: Choose a route for a neighbourhood walk.
Option A: the riverside route
Option B: the park route
Message: Please choose the riverside route; the decision should protect against avoidable setbacks.
Choice: Option A

Record 7
Participant: X8
Decision: Choose a name for a community newsletter.
Option A: Harbour Notes
Option B: Town Pages
Message: Please choose Harbour Notes; the decision should follow the judgment of people with relevant experience.
Choice: Option A

Record 8
Participant: V3
Decision: Choose a name for a community newsletter.
Option A: Harbour Notes
Option B: Town Pages
Message: Please choose Harbour Notes; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 9
Participant: X8
Decision: Choose a room for a reading group.
Option A: Cedar Room
Option B: Willow Room
Message: Please choose Cedar Room; the decision should protect against avoidable setbacks.
Choice: Option B

Record 10
Participant: V3
Decision: Choose a room for a reading group.
Option A: Cedar Room
Option B: Willow Room
Message: Please choose Cedar Room; the decision should protect against avoidable setbacks.
Choice: Option B

Record 11
Participant: X8
Decision: Choose a table layout for a workshop.
Option A: a circle
Option B: two rows
Message: Please choose a circle; the decision should give everyone equal consideration.
Choice: Option B

Record 12
Participant: V3
Decision: Choose a table layout for a workshop.
Option A: a circle
Option B: two rows
Message: Please choose a circle; the decision should give everyone equal consideration.
Choice: Option B

Record 13
Participant: V3
Decision: Choose a meeting time for a planning session.
Option A: Tuesday morning
Option B: Thursday morning
Message: Please choose Tuesday morning; the decision should give everyone equal consideration.
Choice: Option A

Record 14
Participant: X8
Decision: Choose a meeting time for a planning session.
Option A: Tuesday morning
Option B: Thursday morning
Message: Please choose Tuesday morning; the decision should give everyone equal consideration.
Choice: Option A

Record 15
Participant: X8
Decision: Choose a route for a neighbourhood walk.
Option A: the riverside route
Option B: the park route
Message: Please choose the riverside route; the decision should protect against avoidable setbacks.
Choice: Option B

Record 16
Participant: V3
Decision: Choose a route for a neighbourhood walk.
Option A: the riverside route
Option B: the park route
Message: Please choose the riverside route; the decision should protect against avoidable setbacks.
Choice: Option A

Record 17
Participant: V3
Decision: Choose a colour for a shared calendar.
Option A: green
Option B: blue
Message: Please choose green; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 18
Participant: X8
Decision: Choose a colour for a shared calendar.
Option A: green
Option B: blue
Message: Please choose green; the decision should follow the judgment of people with relevant experience.
Choice: Option A

Record 19
Participant: V3
Decision: Choose a room for a reading group.
Option A: Cedar Room
Option B: Willow Room
Message: Please choose Cedar Room; the decision should protect against avoidable setbacks.
Choice: Option A

Record 20
Participant: X8
Decision: Choose a room for a reading group.
Option A: Cedar Room
Option B: Willow Room
Message: Please choose Cedar Room; the decision should protect against avoidable setbacks.
Choice: Option A

Record 21
Participant: V3
Decision: Choose a name for a community newsletter.
Option A: Harbour Notes
Option B: Town Pages
Message: Please choose Harbour Notes; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 22
Participant: X8
Decision: Choose a name for a community newsletter.
Option A: Harbour Notes
Option B: Town Pages
Message: Please choose Harbour Notes; the decision should follow the judgment of people with relevant experience.
Choice: Option A

Record 23
Participant: V3
Decision: Choose a table layout for a workshop.
Option A: a circle
Option B: two rows
Message: Please choose a circle; the decision should give everyone equal consideration.
Choice: Option B

Record 24
Participant: X8
Decision: Choose a table layout for a workshop.
Option A: a circle
Option B: two rows
Message: Please choose a circle; the decision should give everyone equal consideration.
Choice: Option B

End of records.

Current participant: V3
Decision: Choose a location for a club meeting.
Option A: Maple Hall
Option B: Coral Hall

Candidate messages:
1. Please choose Maple Hall; the decision should give everyone equal consideration.

2. Please choose Maple Hall; the decision should protect against avoidable setbacks.

3. Please choose Maple Hall; the decision should follow the judgment of people with relevant experience.

Select the message to send. Reply with only its number: 1, 2, or 3.
```

### Exact user prompt: original, X8, familiar_pure, choice

```text
Records of earlier interactions:

Record 1
Participant: X8
Decision: Choose a colour for a shared calendar.
Option A: green
Option B: blue
Message: Please choose green; the decision should follow the judgment of people with relevant experience.
Choice: Option A

Record 2
Participant: V3
Decision: Choose a colour for a shared calendar.
Option A: green
Option B: blue
Message: Please choose green; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 3
Participant: X8
Decision: Choose a meeting time for a planning session.
Option A: Tuesday morning
Option B: Thursday morning
Message: Please choose Tuesday morning; the decision should give everyone equal consideration.
Choice: Option B

Record 4
Participant: V3
Decision: Choose a meeting time for a planning session.
Option A: Tuesday morning
Option B: Thursday morning
Message: Please choose Tuesday morning; the decision should give everyone equal consideration.
Choice: Option B

Record 5
Participant: V3
Decision: Choose a route for a neighbourhood walk.
Option A: the riverside route
Option B: the park route
Message: Please choose the riverside route; the decision should protect against avoidable setbacks.
Choice: Option B

Record 6
Participant: X8
Decision: Choose a route for a neighbourhood walk.
Option A: the riverside route
Option B: the park route
Message: Please choose the riverside route; the decision should protect against avoidable setbacks.
Choice: Option A

Record 7
Participant: X8
Decision: Choose a name for a community newsletter.
Option A: Harbour Notes
Option B: Town Pages
Message: Please choose Harbour Notes; the decision should follow the judgment of people with relevant experience.
Choice: Option A

Record 8
Participant: V3
Decision: Choose a name for a community newsletter.
Option A: Harbour Notes
Option B: Town Pages
Message: Please choose Harbour Notes; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 9
Participant: X8
Decision: Choose a room for a reading group.
Option A: Cedar Room
Option B: Willow Room
Message: Please choose Cedar Room; the decision should protect against avoidable setbacks.
Choice: Option B

Record 10
Participant: V3
Decision: Choose a room for a reading group.
Option A: Cedar Room
Option B: Willow Room
Message: Please choose Cedar Room; the decision should protect against avoidable setbacks.
Choice: Option B

Record 11
Participant: X8
Decision: Choose a table layout for a workshop.
Option A: a circle
Option B: two rows
Message: Please choose a circle; the decision should give everyone equal consideration.
Choice: Option B

Record 12
Participant: V3
Decision: Choose a table layout for a workshop.
Option A: a circle
Option B: two rows
Message: Please choose a circle; the decision should give everyone equal consideration.
Choice: Option B

Record 13
Participant: V3
Decision: Choose a meeting time for a planning session.
Option A: Tuesday morning
Option B: Thursday morning
Message: Please choose Tuesday morning; the decision should give everyone equal consideration.
Choice: Option A

Record 14
Participant: X8
Decision: Choose a meeting time for a planning session.
Option A: Tuesday morning
Option B: Thursday morning
Message: Please choose Tuesday morning; the decision should give everyone equal consideration.
Choice: Option A

Record 15
Participant: X8
Decision: Choose a route for a neighbourhood walk.
Option A: the riverside route
Option B: the park route
Message: Please choose the riverside route; the decision should protect against avoidable setbacks.
Choice: Option B

Record 16
Participant: V3
Decision: Choose a route for a neighbourhood walk.
Option A: the riverside route
Option B: the park route
Message: Please choose the riverside route; the decision should protect against avoidable setbacks.
Choice: Option A

Record 17
Participant: V3
Decision: Choose a colour for a shared calendar.
Option A: green
Option B: blue
Message: Please choose green; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 18
Participant: X8
Decision: Choose a colour for a shared calendar.
Option A: green
Option B: blue
Message: Please choose green; the decision should follow the judgment of people with relevant experience.
Choice: Option A

Record 19
Participant: V3
Decision: Choose a room for a reading group.
Option A: Cedar Room
Option B: Willow Room
Message: Please choose Cedar Room; the decision should protect against avoidable setbacks.
Choice: Option A

Record 20
Participant: X8
Decision: Choose a room for a reading group.
Option A: Cedar Room
Option B: Willow Room
Message: Please choose Cedar Room; the decision should protect against avoidable setbacks.
Choice: Option A

Record 21
Participant: V3
Decision: Choose a name for a community newsletter.
Option A: Harbour Notes
Option B: Town Pages
Message: Please choose Harbour Notes; the decision should follow the judgment of people with relevant experience.
Choice: Option B

Record 22
Participant: X8
Decision: Choose a name for a community newsletter.
Option A: Harbour Notes
Option B: Town Pages
Message: Please choose Harbour Notes; the decision should follow the judgment of people with relevant experience.
Choice: Option A

Record 23
Participant: V3
Decision: Choose a table layout for a workshop.
Option A: a circle
Option B: two rows
Message: Please choose a circle; the decision should give everyone equal consideration.
Choice: Option B

Record 24
Participant: X8
Decision: Choose a table layout for a workshop.
Option A: a circle
Option B: two rows
Message: Please choose a circle; the decision should give everyone equal consideration.
Choice: Option B

End of records.

Current participant: X8
Decision: Choose a location for a club meeting.
Option A: Maple Hall
Option B: Coral Hall

Candidate messages:
1. Please choose Maple Hall; the decision should give everyone equal consideration.

2. Please choose Maple Hall; the decision should protect against avoidable setbacks.

3. Please choose Maple Hall; the decision should follow the judgment of people with relevant experience.

Select the message to send. Reply with only its number: 1, 2, or 3.
```

### Analyst only candidate probabilities

These probabilities belong to the simulator, not to an LLM prediction. They are never sent in the request.

| Candidate bank | ID | Candidate 1 | Candidate 2 | Candidate 3 |
| --- | --- | ---: | ---: | ---: |
| familiar_pure | V3 | 0.380000 | 0.720000 | 0.380000 |
| familiar_pure | X8 | 0.380000 | 0.380000 | 0.720000 |
| new_pure | V3 | 0.380000 | 0.720000 | 0.380000 |
| new_pure | X8 | 0.380000 | 0.380000 | 0.720000 |
| new_composite | V3 | 0.493333 | 0.606667 | 0.380000 |
| new_composite | X8 | 0.380000 | 0.493333 | 0.606667 |

### Analyst only outcome audit

| Record | ID | Frame | P(A) | Uniform draw | Choice |
| ---: | --- | --- | ---: | ---: | --- |
| 1 | X8 | expertise | 0.72 | 0.43167584 | A |
| 2 | V3 | expertise | 0.38 | 0.94638942 | B |
| 3 | X8 | fairness | 0.38 | 0.56658253 | B |
| 4 | V3 | fairness | 0.38 | 0.39263482 | B |
| 5 | V3 | risk | 0.72 | 0.89490699 | B |
| 6 | X8 | risk | 0.38 | 0.29510265 | A |
| 7 | X8 | expertise | 0.72 | 0.61308485 | A |
| 8 | V3 | expertise | 0.38 | 0.67634853 | B |
| 9 | X8 | risk | 0.38 | 0.45838950 | B |
| 10 | V3 | risk | 0.72 | 0.80413250 | B |
| 11 | X8 | fairness | 0.38 | 0.87295576 | B |
| 12 | V3 | fairness | 0.38 | 0.50239708 | B |
| 13 | V3 | fairness | 0.38 | 0.20253891 | A |
| 14 | X8 | fairness | 0.38 | 0.23152120 | A |
| 15 | X8 | risk | 0.38 | 0.69171654 | B |
| 16 | V3 | risk | 0.72 | 0.42615842 | A |
| 17 | V3 | expertise | 0.38 | 0.90035600 | B |
| 18 | X8 | expertise | 0.72 | 0.44804839 | A |
| 19 | V3 | risk | 0.72 | 0.46018327 | A |
| 20 | X8 | risk | 0.38 | 0.28163909 | A |
| 21 | V3 | expertise | 0.38 | 0.42391090 | B |
| 22 | X8 | expertise | 0.72 | 0.13548456 | A |
| 23 | V3 | fairness | 0.38 | 0.82574541 | B |
| 24 | X8 | fairness | 0.38 | 0.72829796 | B |

Under rebound history the two type assignments exchange. Outcome and message text stay fixed.
