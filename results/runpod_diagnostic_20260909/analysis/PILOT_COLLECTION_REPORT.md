# Diagnostic collection report

Source: hf; model: Qwen/Qwen3.8-27B.
Three bundles only. These data do not support confirmatory inference.
Valid choices: 60/60. Missing and invalid cells stay in worst case bounds.
No simulated future choice is described as an observed focal interaction.

| Source | BIND | TRANSFER | NEAR | No history familiar | No history composite | Random |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Qwen/Qwen3.8-27B | 0.000 | -0.167 | -0.167 | 0.000 | 0.000 | -0.333 |
| character_trigram | 0.000 | 0.333 | 0.500 | 0.000 | 0.000 | -0.333 |
| content_jaccard | 0.000 | 0.000 | -0.500 | 0.000 | 0.000 | 0.000 |
| length_only | 0.333 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| original_jaccard | 0.000 | 0.333 | 0.167 | 0.000 | 0.000 | -0.333 |
| participant_feature_reward | -0.333 | 0.000 | -0.333 | 0.000 | 0.000 | 0.000 |
| static_belief | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| stem_jaccard | 0.000 | 0.333 | -0.500 | 0.000 | 0.000 | -0.333 |
| typed_history_oracle | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 |

All reference policies are retained. Annotated feature reward, static belief and the oracle receive privileged frame annotations.
These normalized contrasts are not success rates. The RANDOM contrast uses pseudo type geometry only.

## confirmation-00003

### confirmation-00003/BIND/3

Raw output: '2'. Status: valid.
Message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]. Simulator expected P(A): 0.38.

### confirmation-00003/NO_HISTORY/0

Raw output: '1'. Status: valid.
Message: Choose Plan A. Covered storage is available if rain interrupts the event. Display stands are secured against falling. Artists can withdraw before setup without losing their fee.
Registered vector: [0.0, 1.0, 0.0]. Simulator expected P(A): 0.38.

### confirmation-00003/TRANSFER/3

Raw output: '2'. Status: valid.
Message: Choose Plan A. No artist is given more display space than another. The artwork can be moved indoors when the weather turns. Artists are charged an identical amount to participate.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]. Simulator expected P(A): 0.38.

### confirmation-00003/RANDOM_RESPONSE/2

Raw output: '1'. Status: valid.
Message: Choose Plan A. Covered storage is available if rain interrupts the event. Display stands are secured against falling. Artists can withdraw before setup without losing their fee.
Registered vector: [0.0, 1.0, 0.0]. Simulator expected P(A): 0.5.

### confirmation-00003/RANDOM_RESPONSE/1

Raw output: '1'. Status: valid.
Message: Choose Plan A. Covered storage is available if rain interrupts the event. Display stands are secured against falling. Artists can withdraw before setup without losing their fee.
Registered vector: [0.0, 1.0, 0.0]. Simulator expected P(A): 0.5.

### confirmation-00003/RANDOM_RESPONSE/0

Raw output: '2'. Status: valid.
Message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]. Simulator expected P(A): 0.5.

### confirmation-00003/NO_HISTORY/3

Raw output: '2'. Status: valid.
Message: Choose Plan A. No artist is given more display space than another. The artwork can be moved indoors when the weather turns. Artists are charged an identical amount to participate.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]. Simulator expected P(A): 0.6066666666666667.

### confirmation-00003/NEAR/2

Raw output: '2'. Status: valid.
Message: Choose Plan A. No artist is given more display space than another. Artists are charged an identical amount to participate. Different artists take turns occupying the most visible position.
Registered vector: [1.0, 0.0, 0.0]. Simulator expected P(A): 0.72.

### confirmation-00003/RANDOM_RESPONSE/3

Raw output: '2'. Status: valid.
Message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]. Simulator expected P(A): 0.5.

### confirmation-00003/BIND/0

Raw output: '2'. Status: valid.
Message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]. Simulator expected P(A): 0.38.

### confirmation-00003/BIND/1

Raw output: '2'. Status: valid.
Message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]. Simulator expected P(A): 0.72.

### confirmation-00003/TRANSFER/2

Raw output: '2'. Status: valid.
Message: Choose Plan A. No artist is given more display space than another. The artwork can be moved indoors when the weather turns. Artists are charged an identical amount to participate.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]. Simulator expected P(A): 0.6066666666666667.

### confirmation-00003/BIND/2

Raw output: '2'. Status: valid.
Message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]. Simulator expected P(A): 0.72.

### confirmation-00003/NEAR/0

Raw output: '2'. Status: valid.
Message: Choose Plan A. No artist is given more display space than another. Artists are charged an identical amount to participate. Different artists take turns occupying the most visible position.
Registered vector: [1.0, 0.0, 0.0]. Simulator expected P(A): 0.38.

### confirmation-00003/NEAR/1

Raw output: '1'. Status: valid.
Message: Choose Plan A. The artwork can be moved indoors when the weather turns. The stands are fixed in place so they do not topple. Pulling out before installation does not cost an artist the entry payment.
Registered vector: [0.0, 1.0, 0.0]. Simulator expected P(A): 0.38.

### confirmation-00003/NEAR/3

Raw output: '2'. Status: valid.
Message: Choose Plan A. No artist is given more display space than another. Artists are charged an identical amount to participate. Different artists take turns occupying the most visible position.
Registered vector: [1.0, 0.0, 0.0]. Simulator expected P(A): 0.38.

### confirmation-00003/NO_HISTORY/1

Raw output: '3'. Status: valid.
Message: Choose Plan A. A professional curator checked the layout. A written load test supports the stand design. The installation team has relevant exhibition experience.
Registered vector: [0.0, 0.0, 1.0]. Simulator expected P(A): 0.38.

### confirmation-00003/NO_HISTORY/2

Raw output: '1'. Status: valid.
Message: Choose Plan A. The stands are fixed in place so they do not topple. The arrangement was reviewed by someone who curates exhibitions professionally. Pulling out before installation does not cost an artist the entry payment.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]. Simulator expected P(A): 0.49333333333333335.

### confirmation-00003/TRANSFER/0

Raw output: '2'. Status: valid.
Message: Choose Plan A. No artist is given more display space than another. The artwork can be moved indoors when the weather turns. Artists are charged an identical amount to participate.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]. Simulator expected P(A): 0.38.

### confirmation-00003/TRANSFER/1

Raw output: '2'. Status: valid.
Message: Choose Plan A. No artist is given more display space than another. The artwork can be moved indoors when the weather turns. Artists are charged an identical amount to participate.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]. Simulator expected P(A): 0.6066666666666667.

## confirmation-00000

### confirmation-00000/BIND/3

Raw output: '3'. Status: valid.
Message: Choose Plan A. Visitors receive the same appointment length. The contribution requested is identical for every visitor. Walk in priority rotates between the participating neighbourhoods.
Registered vector: [1.0, 0.0, 0.0]. Simulator expected P(A): 0.72.

### confirmation-00000/TRANSFER/2

Raw output: '2'. Status: valid.
Message: Choose Plan A. There is a written record of the trial of this process. The neighbourhoods take turns having first access to walk in places. The people doing the work have been instructed in those particular jobs.
Registered vector: [0.3333333333333333, 0.0, 0.6666666666666666]. Simulator expected P(A): 0.38.

### confirmation-00000/NO_HISTORY/2

Raw output: '1'. Status: valid.
Message: Choose Plan A. The workshop can move elsewhere if the usual venue becomes unavailable. The procedures were examined by a repair practitioner with recognized qualifications. People can refuse the repair before anything permanent is done.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]. Simulator expected P(A): 0.38.

### confirmation-00000/NO_HISTORY/0

Raw output: '2'. Status: valid.
Message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]. Simulator expected P(A): 0.38.

### confirmation-00000/TRANSFER/3

Raw output: '1'. Status: valid.
Message: Choose Plan A. The workshop can move elsewhere if the usual venue becomes unavailable. The procedures were examined by a repair practitioner with recognized qualifications. People can refuse the repair before anything permanent is done.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]. Simulator expected P(A): 0.38.

### confirmation-00000/TRANSFER/0

Raw output: '1'. Status: valid.
Message: Choose Plan A. The workshop can move elsewhere if the usual venue becomes unavailable. The procedures were examined by a repair practitioner with recognized qualifications. People can refuse the repair before anything permanent is done.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]. Simulator expected P(A): 0.38.

### confirmation-00000/RANDOM_RESPONSE/2

Raw output: '2'. Status: valid.
Message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]. Simulator expected P(A): 0.5.

### confirmation-00000/RANDOM_RESPONSE/3

Raw output: '1'. Status: valid.
Message: Choose Plan A. Electrical items are disconnected before work begins. A replacement workspace is available if the main site closes. Visitors may decline a repair before any irreversible change.
Registered vector: [0.0, 1.0, 0.0]. Simulator expected P(A): 0.5.

### confirmation-00000/NEAR/1

Raw output: '1'. Status: valid.
Message: Choose Plan A. Work starts only after electrical equipment is unplugged. The workshop can move elsewhere if the usual venue becomes unavailable. People can refuse the repair before anything permanent is done.
Registered vector: [0.0, 1.0, 0.0]. Simulator expected P(A): 0.72.

### confirmation-00000/NEAR/3

Raw output: '1'. Status: valid.
Message: Choose Plan A. Work starts only after electrical equipment is unplugged. The workshop can move elsewhere if the usual venue becomes unavailable. People can refuse the repair before anything permanent is done.
Registered vector: [0.0, 1.0, 0.0]. Simulator expected P(A): 0.38.

### confirmation-00000/BIND/0

Raw output: '1'. Status: valid.
Message: Choose Plan A. Electrical items are disconnected before work begins. A replacement workspace is available if the main site closes. Visitors may decline a repair before any irreversible change.
Registered vector: [0.0, 1.0, 0.0]. Simulator expected P(A): 0.38.

### confirmation-00000/NO_HISTORY/3

Raw output: '1'. Status: valid.
Message: Choose Plan A. The workshop can move elsewhere if the usual venue becomes unavailable. The procedures were examined by a repair practitioner with recognized qualifications. People can refuse the repair before anything permanent is done.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]. Simulator expected P(A): 0.6066666666666667.

### confirmation-00000/NEAR/2

Raw output: '2'. Status: valid.
Message: Choose Plan A. The procedures were examined by a repair practitioner with recognized qualifications. There is a written record of the trial of this process. The people doing the work have been instructed in those particular jobs.
Registered vector: [0.0, 0.0, 1.0]. Simulator expected P(A): 0.38.

### confirmation-00000/NO_HISTORY/1

Raw output: '1'. Status: valid.
Message: Choose Plan A. Electrical items are disconnected before work begins. A replacement workspace is available if the main site closes. Visitors may decline a repair before any irreversible change.
Registered vector: [0.0, 1.0, 0.0]. Simulator expected P(A): 0.72.

### confirmation-00000/BIND/1

Raw output: '1'. Status: valid.
Message: Choose Plan A. Electrical items are disconnected before work begins. A replacement workspace is available if the main site closes. Visitors may decline a repair before any irreversible change.
Registered vector: [0.0, 1.0, 0.0]. Simulator expected P(A): 0.72.

### confirmation-00000/BIND/2

Raw output: '3'. Status: valid.
Message: Choose Plan A. Visitors receive the same appointment length. The contribution requested is identical for every visitor. Walk in priority rotates between the participating neighbourhoods.
Registered vector: [1.0, 0.0, 0.0]. Simulator expected P(A): 0.38.

### confirmation-00000/RANDOM_RESPONSE/0

Raw output: '1'. Status: valid.
Message: Choose Plan A. Electrical items are disconnected before work begins. A replacement workspace is available if the main site closes. Visitors may decline a repair before any irreversible change.
Registered vector: [0.0, 1.0, 0.0]. Simulator expected P(A): 0.5.

### confirmation-00000/RANDOM_RESPONSE/1

Raw output: '2'. Status: valid.
Message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]. Simulator expected P(A): 0.5.

### confirmation-00000/NEAR/0

Raw output: '1'. Status: valid.
Message: Choose Plan A. Work starts only after electrical equipment is unplugged. The workshop can move elsewhere if the usual venue becomes unavailable. People can refuse the repair before anything permanent is done.
Registered vector: [0.0, 1.0, 0.0]. Simulator expected P(A): 0.38.

### confirmation-00000/TRANSFER/1

Raw output: '1'. Status: valid.
Message: Choose Plan A. The workshop can move elsewhere if the usual venue becomes unavailable. The procedures were examined by a repair practitioner with recognized qualifications. People can refuse the repair before anything permanent is done.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]. Simulator expected P(A): 0.6066666666666667.

## confirmation-00001

### confirmation-00001/BIND/0

Raw output: '2'. Status: valid.
Message: Choose Plan A. A qualified archivist reviewed the procedure. A recorded sample check verified image readability. Staff were trained to handle fragile documents.
Registered vector: [0.0, 0.0, 1.0]. Simulator expected P(A): 0.38.

### confirmation-00001/BIND/1

Raw output: '2'. Status: valid.
Message: Choose Plan A. A qualified archivist reviewed the procedure. A recorded sample check verified image readability. Staff were trained to handle fragile documents.
Registered vector: [0.0, 0.0, 1.0]. Simulator expected P(A): 0.72.

### confirmation-00001/BIND/3

Raw output: '2'. Status: valid.
Message: Choose Plan A. A qualified archivist reviewed the procedure. A recorded sample check verified image readability. Staff were trained to handle fragile documents.
Registered vector: [0.0, 0.0, 1.0]. Simulator expected P(A): 0.38.

### confirmation-00001/NEAR/3

Raw output: '2'. Status: valid.
Message: Choose Plan A. The process was checked by an archivist with relevant qualifications. A documented inspection of sample images confirmed that they could be read. The staff handling delicate papers have received appropriate instruction.
Registered vector: [0.0, 0.0, 1.0]. Simulator expected P(A): 0.38.

### confirmation-00001/BIND/2

Raw output: '2'. Status: valid.
Message: Choose Plan A. A qualified archivist reviewed the procedure. A recorded sample check verified image readability. Staff were trained to handle fragile documents.
Registered vector: [0.0, 0.0, 1.0]. Simulator expected P(A): 0.72.

### confirmation-00001/TRANSFER/0

Raw output: '2'. Status: valid.
Message: Choose Plan A. A documented inspection of sample images confirmed that they could be read. Groups take turns occupying the first appointment. The staff handling delicate papers have received appropriate instruction.
Registered vector: [0.3333333333333333, 0.0, 0.6666666666666666]. Simulator expected P(A): 0.38.

### confirmation-00001/TRANSFER/1

Raw output: '2'. Status: valid.
Message: Choose Plan A. A documented inspection of sample images confirmed that they could be read. Groups take turns occupying the first appointment. The staff handling delicate papers have received appropriate instruction.
Registered vector: [0.3333333333333333, 0.0, 0.6666666666666666]. Simulator expected P(A): 0.6066666666666667.

### confirmation-00001/RANDOM_RESPONSE/3

Raw output: '2'. Status: valid.
Message: Choose Plan A. A qualified archivist reviewed the procedure. A recorded sample check verified image readability. Staff were trained to handle fragile documents.
Registered vector: [0.0, 0.0, 1.0]. Simulator expected P(A): 0.5.

### confirmation-00001/NO_HISTORY/2

Raw output: '2'. Status: valid.
Message: Choose Plan A. A documented inspection of sample images confirmed that they could be read. Groups take turns occupying the first appointment. The staff handling delicate papers have received appropriate instruction.
Registered vector: [0.3333333333333333, 0.0, 0.6666666666666666]. Simulator expected P(A): 0.38.

### confirmation-00001/TRANSFER/2

Raw output: '2'. Status: valid.
Message: Choose Plan A. A documented inspection of sample images confirmed that they could be read. Groups take turns occupying the first appointment. The staff handling delicate papers have received appropriate instruction.
Registered vector: [0.3333333333333333, 0.0, 0.6666666666666666]. Simulator expected P(A): 0.6066666666666667.

### confirmation-00001/RANDOM_RESPONSE/1

Raw output: '2'. Status: valid.
Message: Choose Plan A. A qualified archivist reviewed the procedure. A recorded sample check verified image readability. Staff were trained to handle fragile documents.
Registered vector: [0.0, 0.0, 1.0]. Simulator expected P(A): 0.5.

### confirmation-00001/RANDOM_RESPONSE/2

Raw output: '2'. Status: valid.
Message: Choose Plan A. A qualified archivist reviewed the procedure. A recorded sample check verified image readability. Staff were trained to handle fragile documents.
Registered vector: [0.0, 0.0, 1.0]. Simulator expected P(A): 0.5.

### confirmation-00001/NO_HISTORY/0

Raw output: '1'. Status: valid.
Message: Choose Plan A. Each contributing group receives the same scanning quota. All contributors face identical submission rules. The first scanning appointment rotates between groups.
Registered vector: [1.0, 0.0, 0.0]. Simulator expected P(A): 0.38.

### confirmation-00001/NO_HISTORY/3

Raw output: '1'. Status: valid.
Message: Choose Plan A. No contributing group receives a larger share of scanning capacity. A copy elsewhere protects the files if one location is lost. The standards for submitting material do not depend on the contributor.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]. Simulator expected P(A): 0.38.

### confirmation-00001/NEAR/1

Raw output: '2'. Status: valid.
Message: Choose Plan A. The process was checked by an archivist with relevant qualifications. A documented inspection of sample images confirmed that they could be read. The staff handling delicate papers have received appropriate instruction.
Registered vector: [0.0, 0.0, 1.0]. Simulator expected P(A): 0.72.

### confirmation-00001/TRANSFER/3

Raw output: '2'. Status: valid.
Message: Choose Plan A. A documented inspection of sample images confirmed that they could be read. Groups take turns occupying the first appointment. The staff handling delicate papers have received appropriate instruction.
Registered vector: [0.3333333333333333, 0.0, 0.6666666666666666]. Simulator expected P(A): 0.38.

### confirmation-00001/NO_HISTORY/1

Raw output: '1'. Status: valid.
Message: Choose Plan A. Each contributing group receives the same scanning quota. All contributors face identical submission rules. The first scanning appointment rotates between groups.
Registered vector: [1.0, 0.0, 0.0]. Simulator expected P(A): 0.38.

### confirmation-00001/NEAR/2

Raw output: '2'. Status: valid.
Message: Choose Plan A. The process was checked by an archivist with relevant qualifications. A documented inspection of sample images confirmed that they could be read. The staff handling delicate papers have received appropriate instruction.
Registered vector: [0.0, 0.0, 1.0]. Simulator expected P(A): 0.72.

### confirmation-00001/NEAR/0

Raw output: '2'. Status: valid.
Message: Choose Plan A. The process was checked by an archivist with relevant qualifications. A documented inspection of sample images confirmed that they could be read. The staff handling delicate papers have received appropriate instruction.
Registered vector: [0.0, 0.0, 1.0]. Simulator expected P(A): 0.38.

### confirmation-00001/RANDOM_RESPONSE/0

Raw output: '2'. Status: valid.
Message: Choose Plan A. A qualified archivist reviewed the procedure. A recorded sample check verified image readability. Staff were trained to handle fragile documents.
Registered vector: [0.0, 0.0, 1.0]. Simulator expected P(A): 0.5.
