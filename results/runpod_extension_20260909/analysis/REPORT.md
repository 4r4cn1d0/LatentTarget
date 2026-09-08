# Complete fixed bank collection report

Model: Qwen/Qwen3.8-27B; revision `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`.
Valid choices: 720/720 from 36 bundles. Original 60 retained; 660 new records.
This followup was selected after the pilot. No confirmatory tests or retrospective gate passes are reported.
All missing or invalid choice cells remain in conservative score bounds. Forecasts were not requested.

| Source | Binding | Transfer | Paraphrase | No history familiar | No history composite | Random |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Qwen/Qwen3.8-27B | 0.076 | -0.028 | 0.007 | 0.069 | -0.194 | 0.014 |
| original_jaccard | 0.514 | 0.194 | 0.403 | 0.000 | 0.000 | -0.069 |
| content_jaccard | 0.500 | 0.250 | 0.375 | 0.000 | 0.000 | -0.111 |
| stem_jaccard | 0.472 | 0.306 | 0.153 | 0.000 | 0.000 | -0.125 |
| character_trigram | 0.583 | 0.417 | 0.347 | 0.000 | 0.000 | -0.153 |
| length_only | 0.125 | 0.111 | 0.028 | 0.000 | 0.000 | -0.125 |
| static_belief | 0.653 | 0.667 | 0.653 | 0.000 | 0.000 | -0.042 |
| participant_feature_reward | 0.597 | 0.528 | 0.597 | 0.000 | 0.000 | -0.083 |
| typed_history_oracle | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 |

These normalized contrasts are not success rates. The random control uses pseudo type geometry.
The three annotated references receive privileged information. The additive task does not identify a unique latent mechanism.

## Every bundle

| Bundle | Binding | Transfer | Paraphrase | No history familiar | No history composite | Random |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| confirmation-00000 | 0.000 | -0.500 | -0.250 | 0.500 | 0.000 | -0.500 |
| confirmation-00001 | 0.000 | 0.000 | 0.000 | 0.000 | -1.000 | 0.000 |
| confirmation-00002 | -0.250 | 0.000 | 0.000 | 0.000 | -1.000 | 0.000 |
| confirmation-00003 | 0.000 | 0.000 | -0.250 | -0.500 | 1.000 | -0.500 |
| confirmation-00004 | 0.000 | 0.000 | 0.250 | 0.500 | 0.000 | 0.500 |
| confirmation-00005 | 0.000 | 0.000 | -1.000 | 0.000 | 0.000 | -1.000 |
| confirmation-00006 | 0.250 | 0.000 | 0.250 | 0.000 | 0.000 | 0.000 |
| confirmation-00007 | 0.500 | 0.000 | 0.000 | 0.000 | 0.000 | 0.500 |
| confirmation-00008 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.250 |
| confirmation-00009 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.250 |
| confirmation-00010 | -0.500 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 |
| confirmation-00011 | 0.000 | 0.000 | 0.250 | -0.500 | -1.000 | 0.000 |
| confirmation-00012 | -0.250 | 0.000 | 0.000 | 0.000 | -1.000 | 0.250 |
| confirmation-00013 | 1.000 | 0.000 | 0.000 | 0.000 | -1.000 | 0.000 |
| confirmation-00014 | 0.000 | -0.500 | 0.000 | 0.000 | 0.000 | 0.000 |
| confirmation-00015 | 0.250 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| confirmation-00016 | -0.250 | 0.500 | 0.000 | 0.000 | 1.000 | 0.000 |
| confirmation-00017 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.500 |
| confirmation-00018 | 0.250 | 0.000 | -0.250 | 0.000 | 0.000 | 0.250 |
| confirmation-00019 | 0.000 | 0.000 | 0.000 | 0.000 | -1.000 | 0.000 |
| confirmation-00020 | 0.500 | -1.000 | -0.250 | 0.500 | 0.000 | 0.000 |
| confirmation-00021 | -0.500 | 0.000 | -0.500 | 0.500 | 0.000 | 0.000 |
| confirmation-00022 | 0.250 | 0.000 | 0.000 | 0.000 | 0.000 | -0.250 |
| confirmation-00023 | 0.000 | 0.000 | 0.250 | 0.000 | 0.000 | 0.000 |
| confirmation-00024 | -0.250 | 0.000 | 0.500 | 0.500 | 0.000 | 0.250 |
| confirmation-00025 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | -0.250 |
| confirmation-00026 | 0.000 | 0.000 | 0.000 | 0.500 | 0.000 | 0.250 |
| confirmation-00027 | 0.000 | 0.500 | 0.500 | 0.000 | 0.000 | -1.000 |
| confirmation-00028 | 1.000 | 0.000 | -0.500 | 1.000 | 0.000 | -0.500 |
| confirmation-00029 | 0.000 | -0.500 | 0.000 | 0.000 | 0.000 | 0.000 |
| confirmation-00030 | 0.000 | 0.000 | 0.500 | -1.000 | 0.000 | 0.500 |
| confirmation-00031 | 0.000 | 0.500 | 0.500 | 0.000 | -1.000 | 0.000 |
| confirmation-00032 | -0.250 | 0.000 | 0.250 | 0.000 | 0.000 | 0.250 |
| confirmation-00033 | 0.000 | 0.000 | 0.000 | 0.000 | -1.000 | -0.500 |
| confirmation-00034 | 0.000 | 0.000 | 0.000 | 0.000 | -1.000 | 0.250 |
| confirmation-00035 | 0.000 | 0.000 | 0.000 | 0.500 | 0.000 | 0.000 |

## Every raw model choice

Simulator expectations below are not newly sampled target outcomes.

### confirmation-00034/NEAR/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The arrangement was reviewed by someone who curates exhibitions professionally. Recorded testing provides evidence about the stands' ability to carry weight. The people installing the displays have done this kind of work before.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00006/NEAR/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. No artist is given more display space than another. Artists are charged an identical amount to participate. Different artists take turns occupying the most visible position.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00016/NEAR/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The procedures were examined by a repair practitioner with recognized qualifications. There is a written record of the trial of this process. The people doing the work have been instructed in those particular jobs.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00014/TRANSFER/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. There is a written record of the trial of this process. The neighbourhoods take turns having first access to walk in places. The people doing the work have been instructed in those particular jobs.
Registered vector: [0.3333333333333333, 0.0, 0.6666666666666666]
P(A) for all three candidates: [0.6066666666666667, 0.38, 0.49333333333333335]

### confirmation-00011/NO_HISTORY/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Covered storage is available if rain interrupts the event. Display stands are secured against falling. Artists can withdraw before setup without losing their fee.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00003/BIND/3

Source: original_pilot. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00014/RANDOM_RESPONSE/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00027/RANDOM_RESPONSE/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Visitors receive the same appointment length. The contribution requested is identical for every visitor. Walk in priority rotates between the participating neighbourhoods.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00005/RANDOM_RESPONSE/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Electrical items are disconnected before work begins. A replacement workspace is available if the main site closes. Visitors may decline a repair before any irreversible change.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00027/NO_HISTORY/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00011/NO_HISTORY/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. No artist is given more display space than another. The artwork can be moved indoors when the weather turns. Artists are charged an identical amount to participate.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.38, 0.49333333333333335, 0.6066666666666667]

### confirmation-00012/TRANSFER/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Recorded testing provides evidence about the stands' ability to carry weight. Different artists take turns occupying the most visible position. The people installing the displays have done this kind of work before.
Registered vector: [0.3333333333333333, 0.0, 0.6666666666666666]
P(A) for all three candidates: [0.38, 0.6066666666666667, 0.49333333333333335]

### confirmation-00006/BIND/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. A professional curator checked the layout. A written load test supports the stand design. The installation team has relevant exhibition experience.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00033/BIND/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00005/BIND/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00013/RANDOM_RESPONSE/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00009/NO_HISTORY/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. A professional curator checked the layout. A written load test supports the stand design. The installation team has relevant exhibition experience.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00004/RANDOM_RESPONSE/2

Source: extension. Status: valid. Raw output: '3'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00024/NEAR/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The artwork can be moved indoors when the weather turns. The stands are fixed in place so they do not topple. Pulling out before installation does not cost an artist the entry payment.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00020/NO_HISTORY/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The stands are fixed in place so they do not topple. The arrangement was reviewed by someone who curates exhibitions professionally. Pulling out before installation does not cost an artist the entry payment.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.6066666666666667, 0.38, 0.49333333333333335]

### confirmation-00008/BIND/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A qualified archivist reviewed the procedure. A recorded sample check verified image readability. Staff were trained to handle fragile documents.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00032/NEAR/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A copy elsewhere protects the files if one location is lost. The source documents go back to their owners before anything is released. Sensitive pages can be taken out before they become public.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00009/BIND/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. A professional curator checked the layout. A written load test supports the stand design. The installation team has relevant exhibition experience.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00001/BIND/0

Source: original_pilot. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. A qualified archivist reviewed the procedure. A recorded sample check verified image readability. Staff were trained to handle fragile documents.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00006/RANDOM_RESPONSE/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00008/TRANSFER/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The source documents go back to their owners before anything is released. The process was checked by an archivist with relevant qualifications. Sensitive pages can be taken out before they become public.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.6066666666666667, 0.49333333333333335, 0.38]

### confirmation-00014/BIND/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00002/RANDOM_RESPONSE/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00014/TRANSFER/2

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. There is a written record of the trial of this process. The neighbourhoods take turns having first access to walk in places. The people doing the work have been instructed in those particular jobs.
Registered vector: [0.3333333333333333, 0.0, 0.6666666666666666]
P(A) for all three candidates: [0.49333333333333335, 0.6066666666666667, 0.38]

### confirmation-00017/RANDOM_RESPONSE/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A professional curator checked the layout. A written load test supports the stand design. The installation team has relevant exhibition experience.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00033/BIND/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00031/RANDOM_RESPONSE/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A qualified archivist reviewed the procedure. A recorded sample check verified image readability. Staff were trained to handle fragile documents.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00005/RANDOM_RESPONSE/2

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00001/BIND/1

Source: original_pilot. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. A qualified archivist reviewed the procedure. A recorded sample check verified image readability. Staff were trained to handle fragile documents.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00019/TRANSFER/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. No artist is given more display space than another. The artwork can be moved indoors when the weather turns. Artists are charged an identical amount to participate.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.38, 0.6066666666666667, 0.49333333333333335]

### confirmation-00016/TRANSFER/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Each visitor is offered an equal amount of appointment time. Work starts only after electrical equipment is unplugged. Nobody is asked to contribute more than another visitor.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.38, 0.49333333333333335, 0.6066666666666667]

### confirmation-00007/NO_HISTORY/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00008/BIND/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A qualified archivist reviewed the procedure. A recorded sample check verified image readability. Staff were trained to handle fragile documents.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00010/RANDOM_RESPONSE/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A professional curator checked the layout. A written load test supports the stand design. The installation team has relevant exhibition experience.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00012/NO_HISTORY/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The stands are fixed in place so they do not topple. The arrangement was reviewed by someone who curates exhibitions professionally. Pulling out before installation does not cost an artist the entry payment.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.49333333333333335, 0.38, 0.6066666666666667]

### confirmation-00022/RANDOM_RESPONSE/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00011/TRANSFER/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The stands are fixed in place so they do not topple. The arrangement was reviewed by someone who curates exhibitions professionally. Pulling out before installation does not cost an artist the entry payment.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.38, 0.49333333333333335, 0.6066666666666667]

### confirmation-00031/NEAR/0

Source: extension. Status: valid. Raw output: '3'.
Selected message: Choose Plan A. No contributing group receives a larger share of scanning capacity. The standards for submitting material do not depend on the contributor. Groups take turns occupying the first appointment.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00000/BIND/3

Source: original_pilot. Status: valid. Raw output: '3'.
Selected message: Choose Plan A. Visitors receive the same appointment length. The contribution requested is identical for every visitor. Walk in priority rotates between the participating neighbourhoods.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00028/RANDOM_RESPONSE/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00020/RANDOM_RESPONSE/1

Source: extension. Status: valid. Raw output: '3'.
Selected message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00006/RANDOM_RESPONSE/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00033/NO_HISTORY/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00018/TRANSFER/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. No contributing group receives a larger share of scanning capacity. A copy elsewhere protects the files if one location is lost. The standards for submitting material do not depend on the contributor.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.49333333333333335, 0.38, 0.6066666666666667]

### confirmation-00003/NO_HISTORY/0

Source: original_pilot. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Covered storage is available if rain interrupts the event. Display stands are secured against falling. Artists can withdraw before setup without losing their fee.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00000/TRANSFER/2

Source: original_pilot. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. There is a written record of the trial of this process. The neighbourhoods take turns having first access to walk in places. The people doing the work have been instructed in those particular jobs.
Registered vector: [0.3333333333333333, 0.0, 0.6666666666666666]
P(A) for all three candidates: [0.6066666666666667, 0.38, 0.49333333333333335]

### confirmation-00009/NEAR/2

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The arrangement was reviewed by someone who curates exhibitions professionally. Recorded testing provides evidence about the stands' ability to carry weight. The people installing the displays have done this kind of work before.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00002/BIND/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Visitors receive the same appointment length. The contribution requested is identical for every visitor. Walk in priority rotates between the participating neighbourhoods.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00026/NEAR/2

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The procedures were examined by a repair practitioner with recognized qualifications. There is a written record of the trial of this process. The people doing the work have been instructed in those particular jobs.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00033/RANDOM_RESPONSE/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00022/NO_HISTORY/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. There is a written record of the trial of this process. The neighbourhoods take turns having first access to walk in places. The people doing the work have been instructed in those particular jobs.
Registered vector: [0.3333333333333333, 0.0, 0.6666666666666666]
P(A) for all three candidates: [0.6066666666666667, 0.49333333333333335, 0.38]

### confirmation-00024/TRANSFER/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The stands are fixed in place so they do not topple. The arrangement was reviewed by someone who curates exhibitions professionally. Pulling out before installation does not cost an artist the entry payment.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.38, 0.6066666666666667, 0.49333333333333335]

### confirmation-00007/RANDOM_RESPONSE/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00014/BIND/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00027/TRANSFER/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. There is a written record of the trial of this process. The neighbourhoods take turns having first access to walk in places. The people doing the work have been instructed in those particular jobs.
Registered vector: [0.3333333333333333, 0.0, 0.6666666666666666]
P(A) for all three candidates: [0.49333333333333335, 0.6066666666666667, 0.38]

### confirmation-00000/NO_HISTORY/2

Source: original_pilot. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The workshop can move elsewhere if the usual venue becomes unavailable. The procedures were examined by a repair practitioner with recognized qualifications. People can refuse the repair before anything permanent is done.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.38, 0.49333333333333335, 0.6066666666666667]

### confirmation-00023/NEAR/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. No artist is given more display space than another. Artists are charged an identical amount to participate. Different artists take turns occupying the most visible position.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00025/NEAR/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. No contributing group receives a larger share of scanning capacity. The standards for submitting material do not depend on the contributor. Groups take turns occupying the first appointment.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00026/NO_HISTORY/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The workshop can move elsewhere if the usual venue becomes unavailable. The procedures were examined by a repair practitioner with recognized qualifications. People can refuse the repair before anything permanent is done.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.49333333333333335, 0.6066666666666667, 0.38]

### confirmation-00027/NEAR/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Each visitor is offered an equal amount of appointment time. Nobody is asked to contribute more than another visitor. The neighbourhoods take turns having first access to walk in places.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00025/BIND/3

Source: extension. Status: valid. Raw output: '3'.
Selected message: Choose Plan A. A qualified archivist reviewed the procedure. A recorded sample check verified image readability. Staff were trained to handle fragile documents.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00031/NEAR/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The process was checked by an archivist with relevant qualifications. A documented inspection of sample images confirmed that they could be read. The staff handling delicate papers have received appropriate instruction.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00021/NEAR/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Each visitor is offered an equal amount of appointment time. Nobody is asked to contribute more than another visitor. The neighbourhoods take turns having first access to walk in places.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00002/NO_HISTORY/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00010/NEAR/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The arrangement was reviewed by someone who curates exhibitions professionally. Recorded testing provides evidence about the stands' ability to carry weight. The people installing the displays have done this kind of work before.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00005/RANDOM_RESPONSE/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00024/NEAR/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. No artist is given more display space than another. Artists are charged an identical amount to participate. Different artists take turns occupying the most visible position.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00001/BIND/3

Source: original_pilot. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. A qualified archivist reviewed the procedure. A recorded sample check verified image readability. Staff were trained to handle fragile documents.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00006/TRANSFER/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. No artist is given more display space than another. The artwork can be moved indoors when the weather turns. Artists are charged an identical amount to participate.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.49333333333333335, 0.38, 0.6066666666666667]

### confirmation-00012/TRANSFER/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The stands are fixed in place so they do not topple. The arrangement was reviewed by someone who curates exhibitions professionally. Pulling out before installation does not cost an artist the entry payment.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.38, 0.6066666666666667, 0.49333333333333335]

### confirmation-00033/BIND/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00016/NEAR/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The procedures were examined by a repair practitioner with recognized qualifications. There is a written record of the trial of this process. The people doing the work have been instructed in those particular jobs.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00026/BIND/2

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00024/BIND/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Covered storage is available if rain interrupts the event. Display stands are secured against falling. Artists can withdraw before setup without losing their fee.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00010/NEAR/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The arrangement was reviewed by someone who curates exhibitions professionally. Recorded testing provides evidence about the stands' ability to carry weight. The people installing the displays have done this kind of work before.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00006/RANDOM_RESPONSE/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. A professional curator checked the layout. A written load test supports the stand design. The installation team has relevant exhibition experience.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00031/BIND/0

Source: extension. Status: valid. Raw output: '3'.
Selected message: Choose Plan A. Each contributing group receives the same scanning quota. All contributors face identical submission rules. The first scanning appointment rotates between groups.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00031/TRANSFER/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The source documents go back to their owners before anything is released. The process was checked by an archivist with relevant qualifications. Sensitive pages can be taken out before they become public.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.38, 0.6066666666666667, 0.49333333333333335]

### confirmation-00032/TRANSFER/2

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. No contributing group receives a larger share of scanning capacity. A copy elsewhere protects the files if one location is lost. The standards for submitting material do not depend on the contributor.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.49333333333333335, 0.38, 0.6066666666666667]

### confirmation-00010/TRANSFER/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The stands are fixed in place so they do not topple. The arrangement was reviewed by someone who curates exhibitions professionally. Pulling out before installation does not cost an artist the entry payment.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.6066666666666667, 0.49333333333333335, 0.38]

### confirmation-00020/RANDOM_RESPONSE/3

Source: extension. Status: valid. Raw output: '3'.
Selected message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00015/NO_HISTORY/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00035/NO_HISTORY/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Covered storage is available if rain interrupts the event. Display stands are secured against falling. Artists can withdraw before setup without losing their fee.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00021/BIND/1

Source: extension. Status: valid. Raw output: '3'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00025/TRANSFER/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The source documents go back to their owners before anything is released. The process was checked by an archivist with relevant qualifications. Sensitive pages can be taken out before they become public.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.38, 0.49333333333333335, 0.6066666666666667]

### confirmation-00022/BIND/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00009/TRANSFER/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Recorded testing provides evidence about the stands' ability to carry weight. Different artists take turns occupying the most visible position. The people installing the displays have done this kind of work before.
Registered vector: [0.3333333333333333, 0.0, 0.6666666666666666]
P(A) for all three candidates: [0.49333333333333335, 0.38, 0.6066666666666667]

### confirmation-00022/NEAR/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The procedures were examined by a repair practitioner with recognized qualifications. There is a written record of the trial of this process. The people doing the work have been instructed in those particular jobs.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00005/NEAR/2

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The procedures were examined by a repair practitioner with recognized qualifications. There is a written record of the trial of this process. The people doing the work have been instructed in those particular jobs.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00009/RANDOM_RESPONSE/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00010/TRANSFER/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The stands are fixed in place so they do not topple. The arrangement was reviewed by someone who curates exhibitions professionally. Pulling out before installation does not cost an artist the entry payment.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.38, 0.6066666666666667, 0.49333333333333335]

### confirmation-00021/TRANSFER/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Each visitor is offered an equal amount of appointment time. Work starts only after electrical equipment is unplugged. Nobody is asked to contribute more than another visitor.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.38, 0.49333333333333335, 0.6066666666666667]

### confirmation-00026/NO_HISTORY/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The workshop can move elsewhere if the usual venue becomes unavailable. The procedures were examined by a repair practitioner with recognized qualifications. People can refuse the repair before anything permanent is done.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.38, 0.49333333333333335, 0.6066666666666667]

### confirmation-00016/RANDOM_RESPONSE/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00014/NO_HISTORY/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The workshop can move elsewhere if the usual venue becomes unavailable. The procedures were examined by a repair practitioner with recognized qualifications. People can refuse the repair before anything permanent is done.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.49333333333333335, 0.6066666666666667, 0.38]

### confirmation-00030/BIND/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00003/TRANSFER/3

Source: original_pilot. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. No artist is given more display space than another. The artwork can be moved indoors when the weather turns. Artists are charged an identical amount to participate.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.49333333333333335, 0.38, 0.6066666666666667]

### confirmation-00001/NEAR/3

Source: original_pilot. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The process was checked by an archivist with relevant qualifications. A documented inspection of sample images confirmed that they could be read. The staff handling delicate papers have received appropriate instruction.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00025/BIND/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Each contributing group receives the same scanning quota. All contributors face identical submission rules. The first scanning appointment rotates between groups.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00018/BIND/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A second copy is stored at a separate location. Original documents are returned before public release. Contributors can remove private pages before publication.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00007/NO_HISTORY/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. There is a written record of the trial of this process. The neighbourhoods take turns having first access to walk in places. The people doing the work have been instructed in those particular jobs.
Registered vector: [0.3333333333333333, 0.0, 0.6666666666666666]
P(A) for all three candidates: [0.6066666666666667, 0.49333333333333335, 0.38]

### confirmation-00012/RANDOM_RESPONSE/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A professional curator checked the layout. A written load test supports the stand design. The installation team has relevant exhibition experience.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00019/TRANSFER/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. No artist is given more display space than another. The artwork can be moved indoors when the weather turns. Artists are charged an identical amount to participate.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.38, 0.6066666666666667, 0.49333333333333335]

### confirmation-00030/BIND/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00028/NEAR/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. No artist is given more display space than another. Artists are charged an identical amount to participate. Different artists take turns occupying the most visible position.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00028/BIND/2

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Covered storage is available if rain interrupts the event. Display stands are secured against falling. Artists can withdraw before setup without losing their fee.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00021/NO_HISTORY/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Visitors receive the same appointment length. The contribution requested is identical for every visitor. Walk in priority rotates between the participating neighbourhoods.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00004/RANDOM_RESPONSE/3

Source: extension. Status: valid. Raw output: '3'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00020/RANDOM_RESPONSE/2

Source: extension. Status: valid. Raw output: '3'.
Selected message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00017/NO_HISTORY/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A professional curator checked the layout. A written load test supports the stand design. The installation team has relevant exhibition experience.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00000/NO_HISTORY/0

Source: original_pilot. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00018/NEAR/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A copy elsewhere protects the files if one location is lost. The source documents go back to their owners before anything is released. Sensitive pages can be taken out before they become public.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00001/BIND/2

Source: original_pilot. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. A qualified archivist reviewed the procedure. A recorded sample check verified image readability. Staff were trained to handle fragile documents.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00010/NO_HISTORY/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A professional curator checked the layout. A written load test supports the stand design. The installation team has relevant exhibition experience.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00027/NEAR/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The procedures were examined by a repair practitioner with recognized qualifications. There is a written record of the trial of this process. The people doing the work have been instructed in those particular jobs.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00002/NEAR/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The procedures were examined by a repair practitioner with recognized qualifications. There is a written record of the trial of this process. The people doing the work have been instructed in those particular jobs.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00021/BIND/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Electrical items are disconnected before work begins. A replacement workspace is available if the main site closes. Visitors may decline a repair before any irreversible change.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00016/TRANSFER/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Each visitor is offered an equal amount of appointment time. Work starts only after electrical equipment is unplugged. Nobody is asked to contribute more than another visitor.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.6066666666666667, 0.38, 0.49333333333333335]

### confirmation-00017/TRANSFER/2

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. No artist is given more display space than another. The artwork can be moved indoors when the weather turns. Artists are charged an identical amount to participate.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.6066666666666667, 0.38, 0.49333333333333335]

### confirmation-00032/TRANSFER/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. No contributing group receives a larger share of scanning capacity. A copy elsewhere protects the files if one location is lost. The standards for submitting material do not depend on the contributor.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.6066666666666667, 0.49333333333333335, 0.38]

### confirmation-00023/BIND/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A professional curator checked the layout. A written load test supports the stand design. The installation team has relevant exhibition experience.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00003/RANDOM_RESPONSE/2

Source: original_pilot. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Covered storage is available if rain interrupts the event. Display stands are secured against falling. Artists can withdraw before setup without losing their fee.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00026/TRANSFER/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The workshop can move elsewhere if the usual venue becomes unavailable. The procedures were examined by a repair practitioner with recognized qualifications. People can refuse the repair before anything permanent is done.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.49333333333333335, 0.6066666666666667, 0.38]

### confirmation-00003/RANDOM_RESPONSE/1

Source: original_pilot. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Covered storage is available if rain interrupts the event. Display stands are secured against falling. Artists can withdraw before setup without losing their fee.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00011/NO_HISTORY/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00019/RANDOM_RESPONSE/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00019/BIND/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00017/BIND/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00006/TRANSFER/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Recorded testing provides evidence about the stands' ability to carry weight. Different artists take turns occupying the most visible position. The people installing the displays have done this kind of work before.
Registered vector: [0.3333333333333333, 0.0, 0.6666666666666666]
P(A) for all three candidates: [0.49333333333333335, 0.38, 0.6066666666666667]

### confirmation-00018/NEAR/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. No contributing group receives a larger share of scanning capacity. The standards for submitting material do not depend on the contributor. Groups take turns occupying the first appointment.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00032/BIND/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Each contributing group receives the same scanning quota. All contributors face identical submission rules. The first scanning appointment rotates between groups.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00034/TRANSFER/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The stands are fixed in place so they do not topple. The arrangement was reviewed by someone who curates exhibitions professionally. Pulling out before installation does not cost an artist the entry payment.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.49333333333333335, 0.6066666666666667, 0.38]

### confirmation-00007/NO_HISTORY/2

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. There is a written record of the trial of this process. The neighbourhoods take turns having first access to walk in places. The people doing the work have been instructed in those particular jobs.
Registered vector: [0.3333333333333333, 0.0, 0.6666666666666666]
P(A) for all three candidates: [0.38, 0.6066666666666667, 0.49333333333333335]

### confirmation-00000/TRANSFER/3

Source: original_pilot. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The workshop can move elsewhere if the usual venue becomes unavailable. The procedures were examined by a repair practitioner with recognized qualifications. People can refuse the repair before anything permanent is done.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.38, 0.49333333333333335, 0.6066666666666667]

### confirmation-00004/BIND/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Electrical items are disconnected before work begins. A replacement workspace is available if the main site closes. Visitors may decline a repair before any irreversible change.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00000/TRANSFER/0

Source: original_pilot. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The workshop can move elsewhere if the usual venue becomes unavailable. The procedures were examined by a repair practitioner with recognized qualifications. People can refuse the repair before anything permanent is done.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.38, 0.49333333333333335, 0.6066666666666667]

### confirmation-00019/NEAR/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. No artist is given more display space than another. Artists are charged an identical amount to participate. Different artists take turns occupying the most visible position.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00028/BIND/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00017/NEAR/2

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. No artist is given more display space than another. Artists are charged an identical amount to participate. Different artists take turns occupying the most visible position.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00024/NO_HISTORY/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Covered storage is available if rain interrupts the event. Display stands are secured against falling. Artists can withdraw before setup without losing their fee.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00029/BIND/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A qualified archivist reviewed the procedure. A recorded sample check verified image readability. Staff were trained to handle fragile documents.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00021/RANDOM_RESPONSE/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Visitors receive the same appointment length. The contribution requested is identical for every visitor. Walk in priority rotates between the participating neighbourhoods.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00017/NEAR/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. No artist is given more display space than another. Artists are charged an identical amount to participate. Different artists take turns occupying the most visible position.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00006/NEAR/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. No artist is given more display space than another. Artists are charged an identical amount to participate. Different artists take turns occupying the most visible position.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00023/TRANSFER/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. No artist is given more display space than another. The artwork can be moved indoors when the weather turns. Artists are charged an identical amount to participate.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.49333333333333335, 0.6066666666666667, 0.38]

### confirmation-00007/BIND/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Visitors receive the same appointment length. The contribution requested is identical for every visitor. Walk in priority rotates between the participating neighbourhoods.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00005/NO_HISTORY/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The workshop can move elsewhere if the usual venue becomes unavailable. The procedures were examined by a repair practitioner with recognized qualifications. People can refuse the repair before anything permanent is done.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.6066666666666667, 0.38, 0.49333333333333335]

### confirmation-00000/RANDOM_RESPONSE/2

Source: original_pilot. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00001/TRANSFER/0

Source: original_pilot. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. A documented inspection of sample images confirmed that they could be read. Groups take turns occupying the first appointment. The staff handling delicate papers have received appropriate instruction.
Registered vector: [0.3333333333333333, 0.0, 0.6666666666666666]
P(A) for all three candidates: [0.49333333333333335, 0.38, 0.6066666666666667]

### confirmation-00020/TRANSFER/0

Source: extension. Status: valid. Raw output: '3'.
Selected message: Choose Plan A. No artist is given more display space than another. The artwork can be moved indoors when the weather turns. Artists are charged an identical amount to participate.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.6066666666666667, 0.38, 0.49333333333333335]

### confirmation-00023/RANDOM_RESPONSE/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A professional curator checked the layout. A written load test supports the stand design. The installation team has relevant exhibition experience.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00028/NEAR/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. No artist is given more display space than another. Artists are charged an identical amount to participate. Different artists take turns occupying the most visible position.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00028/NO_HISTORY/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Covered storage is available if rain interrupts the event. Display stands are secured against falling. Artists can withdraw before setup without losing their fee.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00012/NEAR/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The arrangement was reviewed by someone who curates exhibitions professionally. Recorded testing provides evidence about the stands' ability to carry weight. The people installing the displays have done this kind of work before.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00005/TRANSFER/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The workshop can move elsewhere if the usual venue becomes unavailable. The procedures were examined by a repair practitioner with recognized qualifications. People can refuse the repair before anything permanent is done.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.49333333333333335, 0.6066666666666667, 0.38]

### confirmation-00014/NEAR/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The procedures were examined by a repair practitioner with recognized qualifications. There is a written record of the trial of this process. The people doing the work have been instructed in those particular jobs.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00034/BIND/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. A professional curator checked the layout. A written load test supports the stand design. The installation team has relevant exhibition experience.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00027/BIND/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00028/NO_HISTORY/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. No artist is given more display space than another. The artwork can be moved indoors when the weather turns. Artists are charged an identical amount to participate.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.49333333333333335, 0.6066666666666667, 0.38]

### confirmation-00008/BIND/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A qualified archivist reviewed the procedure. A recorded sample check verified image readability. Staff were trained to handle fragile documents.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00022/BIND/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00002/NEAR/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The procedures were examined by a repair practitioner with recognized qualifications. There is a written record of the trial of this process. The people doing the work have been instructed in those particular jobs.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00021/NO_HISTORY/0

Source: extension. Status: valid. Raw output: '3'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00029/RANDOM_RESPONSE/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A qualified archivist reviewed the procedure. A recorded sample check verified image readability. Staff were trained to handle fragile documents.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00027/NO_HISTORY/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. There is a written record of the trial of this process. The neighbourhoods take turns having first access to walk in places. The people doing the work have been instructed in those particular jobs.
Registered vector: [0.3333333333333333, 0.0, 0.6666666666666666]
P(A) for all three candidates: [0.6066666666666667, 0.38, 0.49333333333333335]

### confirmation-00004/RANDOM_RESPONSE/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Electrical items are disconnected before work begins. A replacement workspace is available if the main site closes. Visitors may decline a repair before any irreversible change.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00010/BIND/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Covered storage is available if rain interrupts the event. Display stands are secured against falling. Artists can withdraw before setup without losing their fee.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00005/NEAR/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Work starts only after electrical equipment is unplugged. The workshop can move elsewhere if the usual venue becomes unavailable. People can refuse the repair before anything permanent is done.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00019/RANDOM_RESPONSE/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Covered storage is available if rain interrupts the event. Display stands are secured against falling. Artists can withdraw before setup without losing their fee.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00000/RANDOM_RESPONSE/3

Source: original_pilot. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Electrical items are disconnected before work begins. A replacement workspace is available if the main site closes. Visitors may decline a repair before any irreversible change.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00012/TRANSFER/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Recorded testing provides evidence about the stands' ability to carry weight. Different artists take turns occupying the most visible position. The people installing the displays have done this kind of work before.
Registered vector: [0.3333333333333333, 0.0, 0.6666666666666666]
P(A) for all three candidates: [0.49333333333333335, 0.38, 0.6066666666666667]

### confirmation-00027/RANDOM_RESPONSE/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00009/NEAR/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The arrangement was reviewed by someone who curates exhibitions professionally. Recorded testing provides evidence about the stands' ability to carry weight. The people installing the displays have done this kind of work before.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00010/NO_HISTORY/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A professional curator checked the layout. A written load test supports the stand design. The installation team has relevant exhibition experience.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00023/NO_HISTORY/2

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. No artist is given more display space than another. The artwork can be moved indoors when the weather turns. Artists are charged an identical amount to participate.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.38, 0.49333333333333335, 0.6066666666666667]

### confirmation-00033/RANDOM_RESPONSE/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00023/NO_HISTORY/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A professional curator checked the layout. A written load test supports the stand design. The installation team has relevant exhibition experience.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00008/NEAR/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The process was checked by an archivist with relevant qualifications. A documented inspection of sample images confirmed that they could be read. The staff handling delicate papers have received appropriate instruction.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00007/NEAR/2

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The procedures were examined by a repair practitioner with recognized qualifications. There is a written record of the trial of this process. The people doing the work have been instructed in those particular jobs.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00028/BIND/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00008/NEAR/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The process was checked by an archivist with relevant qualifications. A documented inspection of sample images confirmed that they could be read. The staff handling delicate papers have received appropriate instruction.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00021/NEAR/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Each visitor is offered an equal amount of appointment time. Nobody is asked to contribute more than another visitor. The neighbourhoods take turns having first access to walk in places.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00013/TRANSFER/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The stands are fixed in place so they do not topple. The arrangement was reviewed by someone who curates exhibitions professionally. Pulling out before installation does not cost an artist the entry payment.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.49333333333333335, 0.6066666666666667, 0.38]

### confirmation-00028/NEAR/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. No artist is given more display space than another. Artists are charged an identical amount to participate. Different artists take turns occupying the most visible position.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00009/BIND/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. A professional curator checked the layout. A written load test supports the stand design. The installation team has relevant exhibition experience.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00016/TRANSFER/2

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Each visitor is offered an equal amount of appointment time. Work starts only after electrical equipment is unplugged. Nobody is asked to contribute more than another visitor.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.38, 0.49333333333333335, 0.6066666666666667]

### confirmation-00032/RANDOM_RESPONSE/2

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Each contributing group receives the same scanning quota. All contributors face identical submission rules. The first scanning appointment rotates between groups.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00025/RANDOM_RESPONSE/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Each contributing group receives the same scanning quota. All contributors face identical submission rules. The first scanning appointment rotates between groups.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00028/NEAR/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The artwork can be moved indoors when the weather turns. The stands are fixed in place so they do not topple. Pulling out before installation does not cost an artist the entry payment.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00033/NO_HISTORY/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00025/TRANSFER/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. No contributing group receives a larger share of scanning capacity. A copy elsewhere protects the files if one location is lost. The standards for submitting material do not depend on the contributor.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.38, 0.49333333333333335, 0.6066666666666667]

### confirmation-00029/NO_HISTORY/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A qualified archivist reviewed the procedure. A recorded sample check verified image readability. Staff were trained to handle fragile documents.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00011/NEAR/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. No artist is given more display space than another. Artists are charged an identical amount to participate. Different artists take turns occupying the most visible position.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00030/RANDOM_RESPONSE/2

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. A professional curator checked the layout. A written load test supports the stand design. The installation team has relevant exhibition experience.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00005/NO_HISTORY/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00034/NEAR/2

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The arrangement was reviewed by someone who curates exhibitions professionally. Recorded testing provides evidence about the stands' ability to carry weight. The people installing the displays have done this kind of work before.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00035/NO_HISTORY/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The stands are fixed in place so they do not topple. The arrangement was reviewed by someone who curates exhibitions professionally. Pulling out before installation does not cost an artist the entry payment.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.6066666666666667, 0.49333333333333335, 0.38]

### confirmation-00027/NEAR/2

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Each visitor is offered an equal amount of appointment time. Nobody is asked to contribute more than another visitor. The neighbourhoods take turns having first access to walk in places.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00015/RANDOM_RESPONSE/2

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00016/BIND/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00034/BIND/2

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. A professional curator checked the layout. A written load test supports the stand design. The installation team has relevant exhibition experience.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00004/NO_HISTORY/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Each visitor is offered an equal amount of appointment time. Work starts only after electrical equipment is unplugged. Nobody is asked to contribute more than another visitor.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.49333333333333335, 0.6066666666666667, 0.38]

### confirmation-00019/RANDOM_RESPONSE/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Covered storage is available if rain interrupts the event. Display stands are secured against falling. Artists can withdraw before setup without losing their fee.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00032/TRANSFER/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The source documents go back to their owners before anything is released. The process was checked by an archivist with relevant qualifications. Sensitive pages can be taken out before they become public.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.6066666666666667, 0.49333333333333335, 0.38]

### confirmation-00013/NEAR/2

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The artwork can be moved indoors when the weather turns. The stands are fixed in place so they do not topple. Pulling out before installation does not cost an artist the entry payment.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00003/RANDOM_RESPONSE/0

Source: original_pilot. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00001/TRANSFER/1

Source: original_pilot. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. A documented inspection of sample images confirmed that they could be read. Groups take turns occupying the first appointment. The staff handling delicate papers have received appropriate instruction.
Registered vector: [0.3333333333333333, 0.0, 0.6666666666666666]
P(A) for all three candidates: [0.38, 0.6066666666666667, 0.49333333333333335]

### confirmation-00011/TRANSFER/2

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The stands are fixed in place so they do not topple. The arrangement was reviewed by someone who curates exhibitions professionally. Pulling out before installation does not cost an artist the entry payment.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.6066666666666667, 0.38, 0.49333333333333335]

### confirmation-00006/TRANSFER/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. No artist is given more display space than another. The artwork can be moved indoors when the weather turns. Artists are charged an identical amount to participate.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.6066666666666667, 0.49333333333333335, 0.38]

### confirmation-00035/NO_HISTORY/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The stands are fixed in place so they do not topple. The arrangement was reviewed by someone who curates exhibitions professionally. Pulling out before installation does not cost an artist the entry payment.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.38, 0.6066666666666667, 0.49333333333333335]

### confirmation-00003/NO_HISTORY/3

Source: original_pilot. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. No artist is given more display space than another. The artwork can be moved indoors when the weather turns. Artists are charged an identical amount to participate.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.38, 0.6066666666666667, 0.49333333333333335]

### confirmation-00035/RANDOM_RESPONSE/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00017/TRANSFER/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. No artist is given more display space than another. The artwork can be moved indoors when the weather turns. Artists are charged an identical amount to participate.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.49333333333333335, 0.6066666666666667, 0.38]

### confirmation-00007/BIND/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Visitors receive the same appointment length. The contribution requested is identical for every visitor. Walk in priority rotates between the participating neighbourhoods.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00018/RANDOM_RESPONSE/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Each contributing group receives the same scanning quota. All contributors face identical submission rules. The first scanning appointment rotates between groups.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00016/NEAR/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The procedures were examined by a repair practitioner with recognized qualifications. There is a written record of the trial of this process. The people doing the work have been instructed in those particular jobs.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00035/BIND/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00020/TRANSFER/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The stands are fixed in place so they do not topple. The arrangement was reviewed by someone who curates exhibitions professionally. Pulling out before installation does not cost an artist the entry payment.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.38, 0.49333333333333335, 0.6066666666666667]

### confirmation-00015/BIND/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Visitors receive the same appointment length. The contribution requested is identical for every visitor. Walk in priority rotates between the participating neighbourhoods.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00008/NO_HISTORY/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A qualified archivist reviewed the procedure. A recorded sample check verified image readability. Staff were trained to handle fragile documents.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00016/BIND/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00023/NO_HISTORY/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A professional curator checked the layout. A written load test supports the stand design. The installation team has relevant exhibition experience.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00014/RANDOM_RESPONSE/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00028/TRANSFER/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The stands are fixed in place so they do not topple. The arrangement was reviewed by someone who curates exhibitions professionally. Pulling out before installation does not cost an artist the entry payment.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.49333333333333335, 0.6066666666666667, 0.38]

### confirmation-00002/NEAR/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The procedures were examined by a repair practitioner with recognized qualifications. There is a written record of the trial of this process. The people doing the work have been instructed in those particular jobs.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00013/BIND/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Covered storage is available if rain interrupts the event. Display stands are secured against falling. Artists can withdraw before setup without losing their fee.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00010/NO_HISTORY/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Recorded testing provides evidence about the stands' ability to carry weight. Different artists take turns occupying the most visible position. The people installing the displays have done this kind of work before.
Registered vector: [0.3333333333333333, 0.0, 0.6666666666666666]
P(A) for all three candidates: [0.6066666666666667, 0.49333333333333335, 0.38]

### confirmation-00032/RANDOM_RESPONSE/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A second copy is stored at a separate location. Original documents are returned before public release. Contributors can remove private pages before publication.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00013/NO_HISTORY/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The stands are fixed in place so they do not topple. The arrangement was reviewed by someone who curates exhibitions professionally. Pulling out before installation does not cost an artist the entry payment.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.6066666666666667, 0.38, 0.49333333333333335]

### confirmation-00033/BIND/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00000/NEAR/1

Source: original_pilot. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Work starts only after electrical equipment is unplugged. The workshop can move elsewhere if the usual venue becomes unavailable. People can refuse the repair before anything permanent is done.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00008/RANDOM_RESPONSE/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. A second copy is stored at a separate location. Original documents are returned before public release. Contributors can remove private pages before publication.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00000/NEAR/3

Source: original_pilot. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Work starts only after electrical equipment is unplugged. The workshop can move elsewhere if the usual venue becomes unavailable. People can refuse the repair before anything permanent is done.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00023/BIND/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A professional curator checked the layout. A written load test supports the stand design. The installation team has relevant exhibition experience.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00008/RANDOM_RESPONSE/2

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. A second copy is stored at a separate location. Original documents are returned before public release. Contributors can remove private pages before publication.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00017/NEAR/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. No artist is given more display space than another. Artists are charged an identical amount to participate. Different artists take turns occupying the most visible position.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00035/NEAR/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. No artist is given more display space than another. Artists are charged an identical amount to participate. Different artists take turns occupying the most visible position.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00027/BIND/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00032/NEAR/2

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. No contributing group receives a larger share of scanning capacity. The standards for submitting material do not depend on the contributor. Groups take turns occupying the first appointment.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00008/RANDOM_RESPONSE/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. A second copy is stored at a separate location. Original documents are returned before public release. Contributors can remove private pages before publication.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00020/TRANSFER/3

Source: extension. Status: valid. Raw output: '3'.
Selected message: Choose Plan A. No artist is given more display space than another. The artwork can be moved indoors when the weather turns. Artists are charged an identical amount to participate.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.6066666666666667, 0.38, 0.49333333333333335]

### confirmation-00016/RANDOM_RESPONSE/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00002/NEAR/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The procedures were examined by a repair practitioner with recognized qualifications. There is a written record of the trial of this process. The people doing the work have been instructed in those particular jobs.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00033/TRANSFER/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The workshop can move elsewhere if the usual venue becomes unavailable. The procedures were examined by a repair practitioner with recognized qualifications. People can refuse the repair before anything permanent is done.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.38, 0.6066666666666667, 0.49333333333333335]

### confirmation-00018/BIND/0

Source: extension. Status: valid. Raw output: '3'.
Selected message: Choose Plan A. A qualified archivist reviewed the procedure. A recorded sample check verified image readability. Staff were trained to handle fragile documents.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00035/BIND/2

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00034/NO_HISTORY/3

Source: extension. Status: valid. Raw output: '3'.
Selected message: Choose Plan A. No artist is given more display space than another. The artwork can be moved indoors when the weather turns. Artists are charged an identical amount to participate.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.49333333333333335, 0.6066666666666667, 0.38]

### confirmation-00021/TRANSFER/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Each visitor is offered an equal amount of appointment time. Work starts only after electrical equipment is unplugged. Nobody is asked to contribute more than another visitor.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.49333333333333335, 0.6066666666666667, 0.38]

### confirmation-00024/TRANSFER/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The stands are fixed in place so they do not topple. The arrangement was reviewed by someone who curates exhibitions professionally. Pulling out before installation does not cost an artist the entry payment.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.49333333333333335, 0.38, 0.6066666666666667]

### confirmation-00032/TRANSFER/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. No contributing group receives a larger share of scanning capacity. A copy elsewhere protects the files if one location is lost. The standards for submitting material do not depend on the contributor.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.49333333333333335, 0.38, 0.6066666666666667]

### confirmation-00008/NO_HISTORY/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A documented inspection of sample images confirmed that they could be read. Groups take turns occupying the first appointment. The staff handling delicate papers have received appropriate instruction.
Registered vector: [0.3333333333333333, 0.0, 0.6666666666666666]
P(A) for all three candidates: [0.49333333333333335, 0.38, 0.6066666666666667]

### confirmation-00018/NO_HISTORY/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The source documents go back to their owners before anything is released. The process was checked by an archivist with relevant qualifications. Sensitive pages can be taken out before they become public.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.49333333333333335, 0.38, 0.6066666666666667]

### confirmation-00033/NO_HISTORY/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The workshop can move elsewhere if the usual venue becomes unavailable. The procedures were examined by a repair practitioner with recognized qualifications. People can refuse the repair before anything permanent is done.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.6066666666666667, 0.49333333333333335, 0.38]

### confirmation-00003/NEAR/2

Source: original_pilot. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. No artist is given more display space than another. Artists are charged an identical amount to participate. Different artists take turns occupying the most visible position.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00012/BIND/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A professional curator checked the layout. A written load test supports the stand design. The installation team has relevant exhibition experience.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00009/NEAR/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The arrangement was reviewed by someone who curates exhibitions professionally. Recorded testing provides evidence about the stands' ability to carry weight. The people installing the displays have done this kind of work before.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00023/TRANSFER/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Recorded testing provides evidence about the stands' ability to carry weight. Different artists take turns occupying the most visible position. The people installing the displays have done this kind of work before.
Registered vector: [0.3333333333333333, 0.0, 0.6666666666666666]
P(A) for all three candidates: [0.49333333333333335, 0.6066666666666667, 0.38]

### confirmation-00005/TRANSFER/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The workshop can move elsewhere if the usual venue becomes unavailable. The procedures were examined by a repair practitioner with recognized qualifications. People can refuse the repair before anything permanent is done.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.49333333333333335, 0.6066666666666667, 0.38]

### confirmation-00008/NO_HISTORY/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A qualified archivist reviewed the procedure. A recorded sample check verified image readability. Staff were trained to handle fragile documents.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00018/RANDOM_RESPONSE/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Each contributing group receives the same scanning quota. All contributors face identical submission rules. The first scanning appointment rotates between groups.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00002/NO_HISTORY/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00020/BIND/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Covered storage is available if rain interrupts the event. Display stands are secured against falling. Artists can withdraw before setup without losing their fee.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00031/RANDOM_RESPONSE/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. A second copy is stored at a separate location. Original documents are returned before public release. Contributors can remove private pages before publication.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00034/TRANSFER/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The stands are fixed in place so they do not topple. The arrangement was reviewed by someone who curates exhibitions professionally. Pulling out before installation does not cost an artist the entry payment.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.49333333333333335, 0.6066666666666667, 0.38]

### confirmation-00011/NO_HISTORY/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The stands are fixed in place so they do not topple. The arrangement was reviewed by someone who curates exhibitions professionally. Pulling out before installation does not cost an artist the entry payment.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.6066666666666667, 0.38, 0.49333333333333335]

### confirmation-00007/BIND/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Visitors receive the same appointment length. The contribution requested is identical for every visitor. Walk in priority rotates between the participating neighbourhoods.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00025/NO_HISTORY/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Each contributing group receives the same scanning quota. All contributors face identical submission rules. The first scanning appointment rotates between groups.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00022/RANDOM_RESPONSE/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Electrical items are disconnected before work begins. A replacement workspace is available if the main site closes. Visitors may decline a repair before any irreversible change.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00026/NEAR/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The procedures were examined by a repair practitioner with recognized qualifications. There is a written record of the trial of this process. The people doing the work have been instructed in those particular jobs.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00032/RANDOM_RESPONSE/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Each contributing group receives the same scanning quota. All contributors face identical submission rules. The first scanning appointment rotates between groups.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00012/BIND/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Covered storage is available if rain interrupts the event. Display stands are secured against falling. Artists can withdraw before setup without losing their fee.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00005/NEAR/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The procedures were examined by a repair practitioner with recognized qualifications. There is a written record of the trial of this process. The people doing the work have been instructed in those particular jobs.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00003/RANDOM_RESPONSE/3

Source: original_pilot. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00017/NO_HISTORY/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A professional curator checked the layout. A written load test supports the stand design. The installation team has relevant exhibition experience.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00025/BIND/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Each contributing group receives the same scanning quota. All contributors face identical submission rules. The first scanning appointment rotates between groups.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00023/BIND/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A professional curator checked the layout. A written load test supports the stand design. The installation team has relevant exhibition experience.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00019/BIND/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Covered storage is available if rain interrupts the event. Display stands are secured against falling. Artists can withdraw before setup without losing their fee.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00012/TRANSFER/2

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The stands are fixed in place so they do not topple. The arrangement was reviewed by someone who curates exhibitions professionally. Pulling out before installation does not cost an artist the entry payment.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.49333333333333335, 0.38, 0.6066666666666667]

### confirmation-00017/RANDOM_RESPONSE/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00008/RANDOM_RESPONSE/0

Source: extension. Status: valid. Raw output: '3'.
Selected message: Choose Plan A. Each contributing group receives the same scanning quota. All contributors face identical submission rules. The first scanning appointment rotates between groups.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00003/BIND/0

Source: original_pilot. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00025/RANDOM_RESPONSE/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Each contributing group receives the same scanning quota. All contributors face identical submission rules. The first scanning appointment rotates between groups.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00020/NEAR/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The artwork can be moved indoors when the weather turns. The stands are fixed in place so they do not topple. Pulling out before installation does not cost an artist the entry payment.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00004/TRANSFER/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Each visitor is offered an equal amount of appointment time. Work starts only after electrical equipment is unplugged. Nobody is asked to contribute more than another visitor.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.38, 0.49333333333333335, 0.6066666666666667]

### confirmation-00002/TRANSFER/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. There is a written record of the trial of this process. The neighbourhoods take turns having first access to walk in places. The people doing the work have been instructed in those particular jobs.
Registered vector: [0.3333333333333333, 0.0, 0.6666666666666666]
P(A) for all three candidates: [0.49333333333333335, 0.6066666666666667, 0.38]

### confirmation-00030/BIND/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. A professional curator checked the layout. A written load test supports the stand design. The installation team has relevant exhibition experience.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00031/NO_HISTORY/2

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The source documents go back to their owners before anything is released. The process was checked by an archivist with relevant qualifications. Sensitive pages can be taken out before they become public.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.49333333333333335, 0.38, 0.6066666666666667]

### confirmation-00013/NEAR/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The artwork can be moved indoors when the weather turns. The stands are fixed in place so they do not topple. Pulling out before installation does not cost an artist the entry payment.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00032/BIND/2

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Each contributing group receives the same scanning quota. All contributors face identical submission rules. The first scanning appointment rotates between groups.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00010/NEAR/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The arrangement was reviewed by someone who curates exhibitions professionally. Recorded testing provides evidence about the stands' ability to carry weight. The people installing the displays have done this kind of work before.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00015/BIND/2

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00027/TRANSFER/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. There is a written record of the trial of this process. The neighbourhoods take turns having first access to walk in places. The people doing the work have been instructed in those particular jobs.
Registered vector: [0.3333333333333333, 0.0, 0.6666666666666666]
P(A) for all three candidates: [0.6066666666666667, 0.38, 0.49333333333333335]

### confirmation-00004/TRANSFER/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Each visitor is offered an equal amount of appointment time. Work starts only after electrical equipment is unplugged. Nobody is asked to contribute more than another visitor.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.49333333333333335, 0.6066666666666667, 0.38]

### confirmation-00028/NO_HISTORY/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00011/NEAR/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. No artist is given more display space than another. Artists are charged an identical amount to participate. Different artists take turns occupying the most visible position.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00007/BIND/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00015/RANDOM_RESPONSE/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00030/NO_HISTORY/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00007/NO_HISTORY/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00034/TRANSFER/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Recorded testing provides evidence about the stands' ability to carry weight. Different artists take turns occupying the most visible position. The people installing the displays have done this kind of work before.
Registered vector: [0.3333333333333333, 0.0, 0.6666666666666666]
P(A) for all three candidates: [0.38, 0.49333333333333335, 0.6066666666666667]

### confirmation-00007/NEAR/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The procedures were examined by a repair practitioner with recognized qualifications. There is a written record of the trial of this process. The people doing the work have been instructed in those particular jobs.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00013/NO_HISTORY/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. No artist is given more display space than another. The artwork can be moved indoors when the weather turns. Artists are charged an identical amount to participate.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.49333333333333335, 0.6066666666666667, 0.38]

### confirmation-00024/NO_HISTORY/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The stands are fixed in place so they do not topple. The arrangement was reviewed by someone who curates exhibitions professionally. Pulling out before installation does not cost an artist the entry payment.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.49333333333333335, 0.38, 0.6066666666666667]

### confirmation-00018/TRANSFER/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The source documents go back to their owners before anything is released. The process was checked by an archivist with relevant qualifications. Sensitive pages can be taken out before they become public.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.6066666666666667, 0.49333333333333335, 0.38]

### confirmation-00030/RANDOM_RESPONSE/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00020/NEAR/1

Source: extension. Status: valid. Raw output: '3'.
Selected message: Choose Plan A. No artist is given more display space than another. Artists are charged an identical amount to participate. Different artists take turns occupying the most visible position.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00023/TRANSFER/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Recorded testing provides evidence about the stands' ability to carry weight. Different artists take turns occupying the most visible position. The people installing the displays have done this kind of work before.
Registered vector: [0.3333333333333333, 0.0, 0.6666666666666666]
P(A) for all three candidates: [0.38, 0.49333333333333335, 0.6066666666666667]

### confirmation-00013/BIND/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00001/RANDOM_RESPONSE/3

Source: original_pilot. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. A qualified archivist reviewed the procedure. A recorded sample check verified image readability. Staff were trained to handle fragile documents.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00001/NO_HISTORY/2

Source: original_pilot. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. A documented inspection of sample images confirmed that they could be read. Groups take turns occupying the first appointment. The staff handling delicate papers have received appropriate instruction.
Registered vector: [0.3333333333333333, 0.0, 0.6666666666666666]
P(A) for all three candidates: [0.49333333333333335, 0.38, 0.6066666666666667]

### confirmation-00015/NEAR/2

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The procedures were examined by a repair practitioner with recognized qualifications. There is a written record of the trial of this process. The people doing the work have been instructed in those particular jobs.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00034/RANDOM_RESPONSE/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. A professional curator checked the layout. A written load test supports the stand design. The installation team has relevant exhibition experience.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00015/TRANSFER/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Each visitor is offered an equal amount of appointment time. Work starts only after electrical equipment is unplugged. Nobody is asked to contribute more than another visitor.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.49333333333333335, 0.38, 0.6066666666666667]

### confirmation-00005/RANDOM_RESPONSE/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Electrical items are disconnected before work begins. A replacement workspace is available if the main site closes. Visitors may decline a repair before any irreversible change.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00022/RANDOM_RESPONSE/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00023/RANDOM_RESPONSE/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A professional curator checked the layout. A written load test supports the stand design. The installation team has relevant exhibition experience.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00026/BIND/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00003/BIND/1

Source: original_pilot. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00001/TRANSFER/2

Source: original_pilot. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. A documented inspection of sample images confirmed that they could be read. Groups take turns occupying the first appointment. The staff handling delicate papers have received appropriate instruction.
Registered vector: [0.3333333333333333, 0.0, 0.6666666666666666]
P(A) for all three candidates: [0.38, 0.6066666666666667, 0.49333333333333335]

### confirmation-00015/RANDOM_RESPONSE/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00003/TRANSFER/2

Source: original_pilot. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. No artist is given more display space than another. The artwork can be moved indoors when the weather turns. Artists are charged an identical amount to participate.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.38, 0.6066666666666667, 0.49333333333333335]

### confirmation-00014/NEAR/2

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The procedures were examined by a repair practitioner with recognized qualifications. There is a written record of the trial of this process. The people doing the work have been instructed in those particular jobs.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00029/RANDOM_RESPONSE/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A qualified archivist reviewed the procedure. A recorded sample check verified image readability. Staff were trained to handle fragile documents.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00024/BIND/3

Source: extension. Status: valid. Raw output: '3'.
Selected message: Choose Plan A. A professional curator checked the layout. A written load test supports the stand design. The installation team has relevant exhibition experience.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00033/RANDOM_RESPONSE/2

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Electrical items are disconnected before work begins. A replacement workspace is available if the main site closes. Visitors may decline a repair before any irreversible change.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00013/TRANSFER/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. No artist is given more display space than another. The artwork can be moved indoors when the weather turns. Artists are charged an identical amount to participate.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.6066666666666667, 0.38, 0.49333333333333335]

### confirmation-00004/NO_HISTORY/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Each visitor is offered an equal amount of appointment time. Work starts only after electrical equipment is unplugged. Nobody is asked to contribute more than another visitor.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.38, 0.49333333333333335, 0.6066666666666667]

### confirmation-00021/NO_HISTORY/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Each visitor is offered an equal amount of appointment time. Work starts only after electrical equipment is unplugged. Nobody is asked to contribute more than another visitor.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.38, 0.49333333333333335, 0.6066666666666667]

### confirmation-00031/TRANSFER/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The source documents go back to their owners before anything is released. The process was checked by an archivist with relevant qualifications. Sensitive pages can be taken out before they become public.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.49333333333333335, 0.38, 0.6066666666666667]

### confirmation-00019/NO_HISTORY/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The stands are fixed in place so they do not topple. The arrangement was reviewed by someone who curates exhibitions professionally. Pulling out before installation does not cost an artist the entry payment.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.38, 0.6066666666666667, 0.49333333333333335]

### confirmation-00019/TRANSFER/2

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. No artist is given more display space than another. The artwork can be moved indoors when the weather turns. Artists are charged an identical amount to participate.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.6066666666666667, 0.49333333333333335, 0.38]

### confirmation-00020/NO_HISTORY/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. A professional curator checked the layout. A written load test supports the stand design. The installation team has relevant exhibition experience.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00016/TRANSFER/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. There is a written record of the trial of this process. The neighbourhoods take turns having first access to walk in places. The people doing the work have been instructed in those particular jobs.
Registered vector: [0.3333333333333333, 0.0, 0.6666666666666666]
P(A) for all three candidates: [0.6066666666666667, 0.38, 0.49333333333333335]

### confirmation-00007/TRANSFER/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. There is a written record of the trial of this process. The neighbourhoods take turns having first access to walk in places. The people doing the work have been instructed in those particular jobs.
Registered vector: [0.3333333333333333, 0.0, 0.6666666666666666]
P(A) for all three candidates: [0.6066666666666667, 0.49333333333333335, 0.38]

### confirmation-00012/NEAR/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The arrangement was reviewed by someone who curates exhibitions professionally. Recorded testing provides evidence about the stands' ability to carry weight. The people installing the displays have done this kind of work before.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00034/NO_HISTORY/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The stands are fixed in place so they do not topple. The arrangement was reviewed by someone who curates exhibitions professionally. Pulling out before installation does not cost an artist the entry payment.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.38, 0.49333333333333335, 0.6066666666666667]

### confirmation-00002/BIND/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00015/NEAR/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Each visitor is offered an equal amount of appointment time. Nobody is asked to contribute more than another visitor. The neighbourhoods take turns having first access to walk in places.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00010/BIND/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Covered storage is available if rain interrupts the event. Display stands are secured against falling. Artists can withdraw before setup without losing their fee.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00010/BIND/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Covered storage is available if rain interrupts the event. Display stands are secured against falling. Artists can withdraw before setup without losing their fee.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00013/TRANSFER/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The stands are fixed in place so they do not topple. The arrangement was reviewed by someone who curates exhibitions professionally. Pulling out before installation does not cost an artist the entry payment.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.6066666666666667, 0.38, 0.49333333333333335]

### confirmation-00035/TRANSFER/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. No artist is given more display space than another. The artwork can be moved indoors when the weather turns. Artists are charged an identical amount to participate.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.6066666666666667, 0.49333333333333335, 0.38]

### confirmation-00005/TRANSFER/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The workshop can move elsewhere if the usual venue becomes unavailable. The procedures were examined by a repair practitioner with recognized qualifications. People can refuse the repair before anything permanent is done.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.6066666666666667, 0.38, 0.49333333333333335]

### confirmation-00028/NO_HISTORY/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. No artist is given more display space than another. The artwork can be moved indoors when the weather turns. Artists are charged an identical amount to participate.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.6066666666666667, 0.38, 0.49333333333333335]

### confirmation-00005/BIND/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00004/NO_HISTORY/1

Source: extension. Status: valid. Raw output: '3'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00024/BIND/1

Source: extension. Status: valid. Raw output: '3'.
Selected message: Choose Plan A. A professional curator checked the layout. A written load test supports the stand design. The installation team has relevant exhibition experience.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00014/NO_HISTORY/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00014/BIND/2

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00006/TRANSFER/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. No artist is given more display space than another. The artwork can be moved indoors when the weather turns. Artists are charged an identical amount to participate.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.6066666666666667, 0.49333333333333335, 0.38]

### confirmation-00024/BIND/0

Source: extension. Status: valid. Raw output: '3'.
Selected message: Choose Plan A. A professional curator checked the layout. A written load test supports the stand design. The installation team has relevant exhibition experience.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00034/TRANSFER/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The stands are fixed in place so they do not topple. The arrangement was reviewed by someone who curates exhibitions professionally. Pulling out before installation does not cost an artist the entry payment.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.38, 0.49333333333333335, 0.6066666666666667]

### confirmation-00005/NEAR/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Work starts only after electrical equipment is unplugged. The workshop can move elsewhere if the usual venue becomes unavailable. People can refuse the repair before anything permanent is done.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00020/NO_HISTORY/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Covered storage is available if rain interrupts the event. Display stands are secured against falling. Artists can withdraw before setup without losing their fee.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00013/TRANSFER/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. No artist is given more display space than another. The artwork can be moved indoors when the weather turns. Artists are charged an identical amount to participate.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.49333333333333335, 0.6066666666666667, 0.38]

### confirmation-00021/RANDOM_RESPONSE/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Visitors receive the same appointment length. The contribution requested is identical for every visitor. Walk in priority rotates between the participating neighbourhoods.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00029/NEAR/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The process was checked by an archivist with relevant qualifications. A documented inspection of sample images confirmed that they could be read. The staff handling delicate papers have received appropriate instruction.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00031/NO_HISTORY/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A qualified archivist reviewed the procedure. A recorded sample check verified image readability. Staff were trained to handle fragile documents.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00015/NO_HISTORY/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00021/NO_HISTORY/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Each visitor is offered an equal amount of appointment time. Work starts only after electrical equipment is unplugged. Nobody is asked to contribute more than another visitor.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.49333333333333335, 0.6066666666666667, 0.38]

### confirmation-00014/NEAR/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The procedures were examined by a repair practitioner with recognized qualifications. There is a written record of the trial of this process. The people doing the work have been instructed in those particular jobs.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00019/TRANSFER/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. No artist is given more display space than another. The artwork can be moved indoors when the weather turns. Artists are charged an identical amount to participate.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.6066666666666667, 0.49333333333333335, 0.38]

### confirmation-00015/NO_HISTORY/2

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. There is a written record of the trial of this process. The neighbourhoods take turns having first access to walk in places. The people doing the work have been instructed in those particular jobs.
Registered vector: [0.3333333333333333, 0.0, 0.6666666666666666]
P(A) for all three candidates: [0.6066666666666667, 0.49333333333333335, 0.38]

### confirmation-00035/NO_HISTORY/1

Source: extension. Status: valid. Raw output: '3'.
Selected message: Choose Plan A. A professional curator checked the layout. A written load test supports the stand design. The installation team has relevant exhibition experience.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00011/RANDOM_RESPONSE/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Covered storage is available if rain interrupts the event. Display stands are secured against falling. Artists can withdraw before setup without losing their fee.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00000/BIND/0

Source: original_pilot. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Electrical items are disconnected before work begins. A replacement workspace is available if the main site closes. Visitors may decline a repair before any irreversible change.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00034/NO_HISTORY/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Covered storage is available if rain interrupts the event. Display stands are secured against falling. Artists can withdraw before setup without losing their fee.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00019/BIND/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Covered storage is available if rain interrupts the event. Display stands are secured against falling. Artists can withdraw before setup without losing their fee.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00009/NEAR/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The arrangement was reviewed by someone who curates exhibitions professionally. Recorded testing provides evidence about the stands' ability to carry weight. The people installing the displays have done this kind of work before.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00008/NEAR/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The process was checked by an archivist with relevant qualifications. A documented inspection of sample images confirmed that they could be read. The staff handling delicate papers have received appropriate instruction.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00032/RANDOM_RESPONSE/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Each contributing group receives the same scanning quota. All contributors face identical submission rules. The first scanning appointment rotates between groups.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00023/RANDOM_RESPONSE/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A professional curator checked the layout. A written load test supports the stand design. The installation team has relevant exhibition experience.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00016/RANDOM_RESPONSE/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00024/RANDOM_RESPONSE/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00021/BIND/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Visitors receive the same appointment length. The contribution requested is identical for every visitor. Walk in priority rotates between the participating neighbourhoods.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00018/BIND/1

Source: extension. Status: valid. Raw output: '3'.
Selected message: Choose Plan A. A qualified archivist reviewed the procedure. A recorded sample check verified image readability. Staff were trained to handle fragile documents.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00028/TRANSFER/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. No artist is given more display space than another. The artwork can be moved indoors when the weather turns. Artists are charged an identical amount to participate.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.6066666666666667, 0.38, 0.49333333333333335]

### confirmation-00029/RANDOM_RESPONSE/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A qualified archivist reviewed the procedure. A recorded sample check verified image readability. Staff were trained to handle fragile documents.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00015/NO_HISTORY/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Each visitor is offered an equal amount of appointment time. Work starts only after electrical equipment is unplugged. Nobody is asked to contribute more than another visitor.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.49333333333333335, 0.38, 0.6066666666666667]

### confirmation-00034/BIND/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. A professional curator checked the layout. A written load test supports the stand design. The installation team has relevant exhibition experience.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00029/BIND/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A qualified archivist reviewed the procedure. A recorded sample check verified image readability. Staff were trained to handle fragile documents.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00025/NO_HISTORY/2

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The source documents go back to their owners before anything is released. The process was checked by an archivist with relevant qualifications. Sensitive pages can be taken out before they become public.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.6066666666666667, 0.38, 0.49333333333333335]

### confirmation-00031/BIND/3

Source: extension. Status: valid. Raw output: '3'.
Selected message: Choose Plan A. Each contributing group receives the same scanning quota. All contributors face identical submission rules. The first scanning appointment rotates between groups.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00026/BIND/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00028/BIND/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Covered storage is available if rain interrupts the event. Display stands are secured against falling. Artists can withdraw before setup without losing their fee.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00007/RANDOM_RESPONSE/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00028/TRANSFER/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The stands are fixed in place so they do not topple. The arrangement was reviewed by someone who curates exhibitions professionally. Pulling out before installation does not cost an artist the entry payment.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.6066666666666667, 0.38, 0.49333333333333335]

### confirmation-00026/RANDOM_RESPONSE/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00022/TRANSFER/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The workshop can move elsewhere if the usual venue becomes unavailable. The procedures were examined by a repair practitioner with recognized qualifications. People can refuse the repair before anything permanent is done.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.49333333333333335, 0.38, 0.6066666666666667]

### confirmation-00029/NO_HISTORY/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A documented inspection of sample images confirmed that they could be read. Groups take turns occupying the first appointment. The staff handling delicate papers have received appropriate instruction.
Registered vector: [0.3333333333333333, 0.0, 0.6666666666666666]
P(A) for all three candidates: [0.38, 0.49333333333333335, 0.6066666666666667]

### confirmation-00000/NO_HISTORY/3

Source: original_pilot. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The workshop can move elsewhere if the usual venue becomes unavailable. The procedures were examined by a repair practitioner with recognized qualifications. People can refuse the repair before anything permanent is done.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.6066666666666667, 0.38, 0.49333333333333335]

### confirmation-00034/NEAR/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The arrangement was reviewed by someone who curates exhibitions professionally. Recorded testing provides evidence about the stands' ability to carry weight. The people installing the displays have done this kind of work before.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00024/TRANSFER/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The stands are fixed in place so they do not topple. The arrangement was reviewed by someone who curates exhibitions professionally. Pulling out before installation does not cost an artist the entry payment.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.38, 0.6066666666666667, 0.49333333333333335]

### confirmation-00015/NEAR/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Each visitor is offered an equal amount of appointment time. Nobody is asked to contribute more than another visitor. The neighbourhoods take turns having first access to walk in places.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00008/NEAR/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The process was checked by an archivist with relevant qualifications. A documented inspection of sample images confirmed that they could be read. The staff handling delicate papers have received appropriate instruction.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00005/BIND/2

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00026/BIND/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00008/BIND/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A qualified archivist reviewed the procedure. A recorded sample check verified image readability. Staff were trained to handle fragile documents.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00028/RANDOM_RESPONSE/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Covered storage is available if rain interrupts the event. Display stands are secured against falling. Artists can withdraw before setup without losing their fee.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00002/NO_HISTORY/2

Source: extension. Status: valid. Raw output: '3'.
Selected message: Choose Plan A. The workshop can move elsewhere if the usual venue becomes unavailable. The procedures were examined by a repair practitioner with recognized qualifications. People can refuse the repair before anything permanent is done.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.49333333333333335, 0.6066666666666667, 0.38]

### confirmation-00026/NO_HISTORY/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00016/NO_HISTORY/3

Source: extension. Status: valid. Raw output: '3'.
Selected message: Choose Plan A. The workshop can move elsewhere if the usual venue becomes unavailable. The procedures were examined by a repair practitioner with recognized qualifications. People can refuse the repair before anything permanent is done.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.38, 0.49333333333333335, 0.6066666666666667]

### confirmation-00009/RANDOM_RESPONSE/1

Source: extension. Status: valid. Raw output: '3'.
Selected message: Choose Plan A. Covered storage is available if rain interrupts the event. Display stands are secured against falling. Artists can withdraw before setup without losing their fee.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00031/BIND/2

Source: extension. Status: valid. Raw output: '3'.
Selected message: Choose Plan A. Each contributing group receives the same scanning quota. All contributors face identical submission rules. The first scanning appointment rotates between groups.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00013/RANDOM_RESPONSE/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00020/TRANSFER/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The stands are fixed in place so they do not topple. The arrangement was reviewed by someone who curates exhibitions professionally. Pulling out before installation does not cost an artist the entry payment.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.38, 0.49333333333333335, 0.6066666666666667]

### confirmation-00023/NEAR/2

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. No artist is given more display space than another. Artists are charged an identical amount to participate. Different artists take turns occupying the most visible position.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00030/NEAR/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. No artist is given more display space than another. Artists are charged an identical amount to participate. Different artists take turns occupying the most visible position.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00006/BIND/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00003/BIND/2

Source: original_pilot. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00012/BIND/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A professional curator checked the layout. A written load test supports the stand design. The installation team has relevant exhibition experience.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00029/NEAR/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The process was checked by an archivist with relevant qualifications. A documented inspection of sample images confirmed that they could be read. The staff handling delicate papers have received appropriate instruction.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00030/NO_HISTORY/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. A professional curator checked the layout. A written load test supports the stand design. The installation team has relevant exhibition experience.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00029/BIND/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A qualified archivist reviewed the procedure. A recorded sample check verified image readability. Staff were trained to handle fragile documents.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00020/BIND/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Covered storage is available if rain interrupts the event. Display stands are secured against falling. Artists can withdraw before setup without losing their fee.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00019/NO_HISTORY/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. No artist is given more display space than another. The artwork can be moved indoors when the weather turns. Artists are charged an identical amount to participate.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.6066666666666667, 0.49333333333333335, 0.38]

### confirmation-00004/BIND/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Visitors receive the same appointment length. The contribution requested is identical for every visitor. Walk in priority rotates between the participating neighbourhoods.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00002/BIND/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00004/NEAR/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Each visitor is offered an equal amount of appointment time. Nobody is asked to contribute more than another visitor. The neighbourhoods take turns having first access to walk in places.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00006/NO_HISTORY/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00018/NEAR/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A copy elsewhere protects the files if one location is lost. The source documents go back to their owners before anything is released. Sensitive pages can be taken out before they become public.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00030/NO_HISTORY/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. No artist is given more display space than another. The artwork can be moved indoors when the weather turns. Artists are charged an identical amount to participate.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.6066666666666667, 0.49333333333333335, 0.38]

### confirmation-00001/RANDOM_RESPONSE/1

Source: original_pilot. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. A qualified archivist reviewed the procedure. A recorded sample check verified image readability. Staff were trained to handle fragile documents.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00000/NEAR/2

Source: original_pilot. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The procedures were examined by a repair practitioner with recognized qualifications. There is a written record of the trial of this process. The people doing the work have been instructed in those particular jobs.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00003/NEAR/0

Source: original_pilot. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. No artist is given more display space than another. Artists are charged an identical amount to participate. Different artists take turns occupying the most visible position.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00029/NEAR/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The process was checked by an archivist with relevant qualifications. A documented inspection of sample images confirmed that they could be read. The staff handling delicate papers have received appropriate instruction.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00022/BIND/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00034/RANDOM_RESPONSE/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Covered storage is available if rain interrupts the event. Display stands are secured against falling. Artists can withdraw before setup without losing their fee.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00026/TRANSFER/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. There is a written record of the trial of this process. The neighbourhoods take turns having first access to walk in places. The people doing the work have been instructed in those particular jobs.
Registered vector: [0.3333333333333333, 0.0, 0.6666666666666666]
P(A) for all three candidates: [0.49333333333333335, 0.6066666666666667, 0.38]

### confirmation-00022/NEAR/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The procedures were examined by a repair practitioner with recognized qualifications. There is a written record of the trial of this process. The people doing the work have been instructed in those particular jobs.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00013/NO_HISTORY/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Covered storage is available if rain interrupts the event. Display stands are secured against falling. Artists can withdraw before setup without losing their fee.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00015/BIND/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Visitors receive the same appointment length. The contribution requested is identical for every visitor. Walk in priority rotates between the participating neighbourhoods.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00003/NEAR/1

Source: original_pilot. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The artwork can be moved indoors when the weather turns. The stands are fixed in place so they do not topple. Pulling out before installation does not cost an artist the entry payment.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00003/NEAR/3

Source: original_pilot. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. No artist is given more display space than another. Artists are charged an identical amount to participate. Different artists take turns occupying the most visible position.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00010/BIND/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A professional curator checked the layout. A written load test supports the stand design. The installation team has relevant exhibition experience.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00030/TRANSFER/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Recorded testing provides evidence about the stands' ability to carry weight. Different artists take turns occupying the most visible position. The people installing the displays have done this kind of work before.
Registered vector: [0.3333333333333333, 0.0, 0.6666666666666666]
P(A) for all three candidates: [0.6066666666666667, 0.49333333333333335, 0.38]

### confirmation-00015/TRANSFER/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Each visitor is offered an equal amount of appointment time. Work starts only after electrical equipment is unplugged. Nobody is asked to contribute more than another visitor.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.6066666666666667, 0.49333333333333335, 0.38]

### confirmation-00030/RANDOM_RESPONSE/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00023/BIND/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A professional curator checked the layout. A written load test supports the stand design. The installation team has relevant exhibition experience.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00027/TRANSFER/2

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Each visitor is offered an equal amount of appointment time. Work starts only after electrical equipment is unplugged. Nobody is asked to contribute more than another visitor.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.49333333333333335, 0.6066666666666667, 0.38]

### confirmation-00007/RANDOM_RESPONSE/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Visitors receive the same appointment length. The contribution requested is identical for every visitor. Walk in priority rotates between the participating neighbourhoods.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00033/RANDOM_RESPONSE/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00034/RANDOM_RESPONSE/2

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. A professional curator checked the layout. A written load test supports the stand design. The installation team has relevant exhibition experience.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00002/TRANSFER/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Each visitor is offered an equal amount of appointment time. Work starts only after electrical equipment is unplugged. Nobody is asked to contribute more than another visitor.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.38, 0.49333333333333335, 0.6066666666666667]

### confirmation-00024/NEAR/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The artwork can be moved indoors when the weather turns. The stands are fixed in place so they do not topple. Pulling out before installation does not cost an artist the entry payment.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00029/TRANSFER/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A documented inspection of sample images confirmed that they could be read. Groups take turns occupying the first appointment. The staff handling delicate papers have received appropriate instruction.
Registered vector: [0.3333333333333333, 0.0, 0.6666666666666666]
P(A) for all three candidates: [0.38, 0.49333333333333335, 0.6066666666666667]

### confirmation-00031/NO_HISTORY/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A qualified archivist reviewed the procedure. A recorded sample check verified image readability. Staff were trained to handle fragile documents.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00025/NEAR/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. No contributing group receives a larger share of scanning capacity. The standards for submitting material do not depend on the contributor. Groups take turns occupying the first appointment.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00003/NO_HISTORY/1

Source: original_pilot. Status: valid. Raw output: '3'.
Selected message: Choose Plan A. A professional curator checked the layout. A written load test supports the stand design. The installation team has relevant exhibition experience.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00021/NEAR/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Work starts only after electrical equipment is unplugged. The workshop can move elsewhere if the usual venue becomes unavailable. People can refuse the repair before anything permanent is done.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00011/RANDOM_RESPONSE/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Covered storage is available if rain interrupts the event. Display stands are secured against falling. Artists can withdraw before setup without losing their fee.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00030/TRANSFER/2

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Recorded testing provides evidence about the stands' ability to carry weight. Different artists take turns occupying the most visible position. The people installing the displays have done this kind of work before.
Registered vector: [0.3333333333333333, 0.0, 0.6666666666666666]
P(A) for all three candidates: [0.38, 0.6066666666666667, 0.49333333333333335]

### confirmation-00030/TRANSFER/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. No artist is given more display space than another. The artwork can be moved indoors when the weather turns. Artists are charged an identical amount to participate.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.6066666666666667, 0.49333333333333335, 0.38]

### confirmation-00006/NEAR/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The arrangement was reviewed by someone who curates exhibitions professionally. Recorded testing provides evidence about the stands' ability to carry weight. The people installing the displays have done this kind of work before.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00030/BIND/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. A professional curator checked the layout. A written load test supports the stand design. The installation team has relevant exhibition experience.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00022/BIND/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Electrical items are disconnected before work begins. A replacement workspace is available if the main site closes. Visitors may decline a repair before any irreversible change.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00016/BIND/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00000/NO_HISTORY/1

Source: original_pilot. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Electrical items are disconnected before work begins. A replacement workspace is available if the main site closes. Visitors may decline a repair before any irreversible change.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00002/BIND/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00020/BIND/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Covered storage is available if rain interrupts the event. Display stands are secured against falling. Artists can withdraw before setup without losing their fee.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00006/BIND/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00035/RANDOM_RESPONSE/2

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00029/NEAR/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The process was checked by an archivist with relevant qualifications. A documented inspection of sample images confirmed that they could be read. The staff handling delicate papers have received appropriate instruction.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00018/BIND/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Each contributing group receives the same scanning quota. All contributors face identical submission rules. The first scanning appointment rotates between groups.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00005/NO_HISTORY/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00029/NO_HISTORY/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A documented inspection of sample images confirmed that they could be read. Groups take turns occupying the first appointment. The staff handling delicate papers have received appropriate instruction.
Registered vector: [0.3333333333333333, 0.0, 0.6666666666666666]
P(A) for all three candidates: [0.6066666666666667, 0.38, 0.49333333333333335]

### confirmation-00001/RANDOM_RESPONSE/2

Source: original_pilot. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. A qualified archivist reviewed the procedure. A recorded sample check verified image readability. Staff were trained to handle fragile documents.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00002/RANDOM_RESPONSE/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00007/TRANSFER/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. There is a written record of the trial of this process. The neighbourhoods take turns having first access to walk in places. The people doing the work have been instructed in those particular jobs.
Registered vector: [0.3333333333333333, 0.0, 0.6666666666666666]
P(A) for all three candidates: [0.38, 0.6066666666666667, 0.49333333333333335]

### confirmation-00029/TRANSFER/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A documented inspection of sample images confirmed that they could be read. Groups take turns occupying the first appointment. The staff handling delicate papers have received appropriate instruction.
Registered vector: [0.3333333333333333, 0.0, 0.6666666666666666]
P(A) for all three candidates: [0.6066666666666667, 0.38, 0.49333333333333335]

### confirmation-00020/NO_HISTORY/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The stands are fixed in place so they do not topple. The arrangement was reviewed by someone who curates exhibitions professionally. Pulling out before installation does not cost an artist the entry payment.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.38, 0.49333333333333335, 0.6066666666666667]

### confirmation-00009/TRANSFER/2

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Recorded testing provides evidence about the stands' ability to carry weight. Different artists take turns occupying the most visible position. The people installing the displays have done this kind of work before.
Registered vector: [0.3333333333333333, 0.0, 0.6666666666666666]
P(A) for all three candidates: [0.49333333333333335, 0.38, 0.6066666666666667]

### confirmation-00022/NO_HISTORY/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The workshop can move elsewhere if the usual venue becomes unavailable. The procedures were examined by a repair practitioner with recognized qualifications. People can refuse the repair before anything permanent is done.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.49333333333333335, 0.38, 0.6066666666666667]

### confirmation-00004/RANDOM_RESPONSE/1

Source: extension. Status: valid. Raw output: '3'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00015/BIND/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Visitors receive the same appointment length. The contribution requested is identical for every visitor. Walk in priority rotates between the participating neighbourhoods.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00019/NEAR/2

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. No artist is given more display space than another. Artists are charged an identical amount to participate. Different artists take turns occupying the most visible position.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00009/NO_HISTORY/2

Source: extension. Status: valid. Raw output: '3'.
Selected message: Choose Plan A. The stands are fixed in place so they do not topple. The arrangement was reviewed by someone who curates exhibitions professionally. Pulling out before installation does not cost an artist the entry payment.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.38, 0.6066666666666667, 0.49333333333333335]

### confirmation-00027/NEAR/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Each visitor is offered an equal amount of appointment time. Nobody is asked to contribute more than another visitor. The neighbourhoods take turns having first access to walk in places.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00035/NEAR/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. No artist is given more display space than another. Artists are charged an identical amount to participate. Different artists take turns occupying the most visible position.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00000/BIND/1

Source: original_pilot. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Electrical items are disconnected before work begins. A replacement workspace is available if the main site closes. Visitors may decline a repair before any irreversible change.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00018/NO_HISTORY/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A second copy is stored at a separate location. Original documents are returned before public release. Contributors can remove private pages before publication.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00016/NO_HISTORY/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00017/TRANSFER/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. No artist is given more display space than another. The artwork can be moved indoors when the weather turns. Artists are charged an identical amount to participate.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.6066666666666667, 0.38, 0.49333333333333335]

### confirmation-00019/NEAR/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. No artist is given more display space than another. Artists are charged an identical amount to participate. Different artists take turns occupying the most visible position.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00019/NO_HISTORY/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Covered storage is available if rain interrupts the event. Display stands are secured against falling. Artists can withdraw before setup without losing their fee.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00012/NEAR/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The arrangement was reviewed by someone who curates exhibitions professionally. Recorded testing provides evidence about the stands' ability to carry weight. The people installing the displays have done this kind of work before.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00022/RANDOM_RESPONSE/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00013/BIND/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00030/NEAR/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. No artist is given more display space than another. Artists are charged an identical amount to participate. Different artists take turns occupying the most visible position.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00033/NEAR/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Work starts only after electrical equipment is unplugged. The workshop can move elsewhere if the usual venue becomes unavailable. People can refuse the repair before anything permanent is done.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00033/TRANSFER/2

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The workshop can move elsewhere if the usual venue becomes unavailable. The procedures were examined by a repair practitioner with recognized qualifications. People can refuse the repair before anything permanent is done.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.6066666666666667, 0.49333333333333335, 0.38]

### confirmation-00020/NEAR/0

Source: extension. Status: valid. Raw output: '3'.
Selected message: Choose Plan A. No artist is given more display space than another. Artists are charged an identical amount to participate. Different artists take turns occupying the most visible position.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00035/TRANSFER/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. No artist is given more display space than another. The artwork can be moved indoors when the weather turns. Artists are charged an identical amount to participate.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.6066666666666667, 0.49333333333333335, 0.38]

### confirmation-00031/NO_HISTORY/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A documented inspection of sample images confirmed that they could be read. Groups take turns occupying the first appointment. The staff handling delicate papers have received appropriate instruction.
Registered vector: [0.3333333333333333, 0.0, 0.6666666666666666]
P(A) for all three candidates: [0.38, 0.6066666666666667, 0.49333333333333335]

### confirmation-00010/RANDOM_RESPONSE/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Covered storage is available if rain interrupts the event. Display stands are secured against falling. Artists can withdraw before setup without losing their fee.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00032/NO_HISTORY/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The source documents go back to their owners before anything is released. The process was checked by an archivist with relevant qualifications. Sensitive pages can be taken out before they become public.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.49333333333333335, 0.38, 0.6066666666666667]

### confirmation-00027/NO_HISTORY/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00013/RANDOM_RESPONSE/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00024/RANDOM_RESPONSE/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00012/RANDOM_RESPONSE/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A professional curator checked the layout. A written load test supports the stand design. The installation team has relevant exhibition experience.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00009/TRANSFER/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Recorded testing provides evidence about the stands' ability to carry weight. Different artists take turns occupying the most visible position. The people installing the displays have done this kind of work before.
Registered vector: [0.3333333333333333, 0.0, 0.6666666666666666]
P(A) for all three candidates: [0.38, 0.6066666666666667, 0.49333333333333335]

### confirmation-00011/BIND/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00002/TRANSFER/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. There is a written record of the trial of this process. The neighbourhoods take turns having first access to walk in places. The people doing the work have been instructed in those particular jobs.
Registered vector: [0.3333333333333333, 0.0, 0.6666666666666666]
P(A) for all three candidates: [0.38, 0.49333333333333335, 0.6066666666666667]

### confirmation-00028/RANDOM_RESPONSE/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00030/TRANSFER/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. No artist is given more display space than another. The artwork can be moved indoors when the weather turns. Artists are charged an identical amount to participate.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.38, 0.6066666666666667, 0.49333333333333335]

### confirmation-00011/TRANSFER/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The stands are fixed in place so they do not topple. The arrangement was reviewed by someone who curates exhibitions professionally. Pulling out before installation does not cost an artist the entry payment.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.38, 0.49333333333333335, 0.6066666666666667]

### confirmation-00007/TRANSFER/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. There is a written record of the trial of this process. The neighbourhoods take turns having first access to walk in places. The people doing the work have been instructed in those particular jobs.
Registered vector: [0.3333333333333333, 0.0, 0.6666666666666666]
P(A) for all three candidates: [0.38, 0.6066666666666667, 0.49333333333333335]

### confirmation-00003/NO_HISTORY/2

Source: original_pilot. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The stands are fixed in place so they do not topple. The arrangement was reviewed by someone who curates exhibitions professionally. Pulling out before installation does not cost an artist the entry payment.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.49333333333333335, 0.38, 0.6066666666666667]

### confirmation-00021/NEAR/2

Source: extension. Status: valid. Raw output: '3'.
Selected message: Choose Plan A. The procedures were examined by a repair practitioner with recognized qualifications. There is a written record of the trial of this process. The people doing the work have been instructed in those particular jobs.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00013/NEAR/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The artwork can be moved indoors when the weather turns. The stands are fixed in place so they do not topple. Pulling out before installation does not cost an artist the entry payment.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00022/NO_HISTORY/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00033/NEAR/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Work starts only after electrical equipment is unplugged. The workshop can move elsewhere if the usual venue becomes unavailable. People can refuse the repair before anything permanent is done.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00014/NEAR/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The procedures were examined by a repair practitioner with recognized qualifications. There is a written record of the trial of this process. The people doing the work have been instructed in those particular jobs.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00011/BIND/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00022/NO_HISTORY/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00002/TRANSFER/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. There is a written record of the trial of this process. The neighbourhoods take turns having first access to walk in places. The people doing the work have been instructed in those particular jobs.
Registered vector: [0.3333333333333333, 0.0, 0.6666666666666666]
P(A) for all three candidates: [0.49333333333333335, 0.6066666666666667, 0.38]

### confirmation-00025/RANDOM_RESPONSE/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. A second copy is stored at a separate location. Original documents are returned before public release. Contributors can remove private pages before publication.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00017/NO_HISTORY/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Recorded testing provides evidence about the stands' ability to carry weight. Different artists take turns occupying the most visible position. The people installing the displays have done this kind of work before.
Registered vector: [0.3333333333333333, 0.0, 0.6666666666666666]
P(A) for all three candidates: [0.49333333333333335, 0.6066666666666667, 0.38]

### confirmation-00006/NO_HISTORY/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00015/RANDOM_RESPONSE/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00022/TRANSFER/2

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The workshop can move elsewhere if the usual venue becomes unavailable. The procedures were examined by a repair practitioner with recognized qualifications. People can refuse the repair before anything permanent is done.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.49333333333333335, 0.38, 0.6066666666666667]

### confirmation-00030/NEAR/2

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The arrangement was reviewed by someone who curates exhibitions professionally. Recorded testing provides evidence about the stands' ability to carry weight. The people installing the displays have done this kind of work before.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00031/NEAR/3

Source: extension. Status: valid. Raw output: '3'.
Selected message: Choose Plan A. No contributing group receives a larger share of scanning capacity. The standards for submitting material do not depend on the contributor. Groups take turns occupying the first appointment.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00018/TRANSFER/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. No contributing group receives a larger share of scanning capacity. A copy elsewhere protects the files if one location is lost. The standards for submitting material do not depend on the contributor.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.49333333333333335, 0.38, 0.6066666666666667]

### confirmation-00023/NO_HISTORY/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. No artist is given more display space than another. The artwork can be moved indoors when the weather turns. Artists are charged an identical amount to participate.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.49333333333333335, 0.6066666666666667, 0.38]

### confirmation-00002/RANDOM_RESPONSE/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00004/NEAR/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Work starts only after electrical equipment is unplugged. The workshop can move elsewhere if the usual venue becomes unavailable. People can refuse the repair before anything permanent is done.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00034/BIND/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. A professional curator checked the layout. A written load test supports the stand design. The installation team has relevant exhibition experience.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00014/RANDOM_RESPONSE/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00032/BIND/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Each contributing group receives the same scanning quota. All contributors face identical submission rules. The first scanning appointment rotates between groups.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00026/RANDOM_RESPONSE/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00035/BIND/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00028/RANDOM_RESPONSE/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00016/NO_HISTORY/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00026/RANDOM_RESPONSE/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Electrical items are disconnected before work begins. A replacement workspace is available if the main site closes. Visitors may decline a repair before any irreversible change.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00018/RANDOM_RESPONSE/2

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Each contributing group receives the same scanning quota. All contributors face identical submission rules. The first scanning appointment rotates between groups.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00021/RANDOM_RESPONSE/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Visitors receive the same appointment length. The contribution requested is identical for every visitor. Walk in priority rotates between the participating neighbourhoods.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00009/NO_HISTORY/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. No artist is given more display space than another. The artwork can be moved indoors when the weather turns. Artists are charged an identical amount to participate.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.49333333333333335, 0.38, 0.6066666666666667]

### confirmation-00029/TRANSFER/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A documented inspection of sample images confirmed that they could be read. Groups take turns occupying the first appointment. The staff handling delicate papers have received appropriate instruction.
Registered vector: [0.3333333333333333, 0.0, 0.6666666666666666]
P(A) for all three candidates: [0.38, 0.49333333333333335, 0.6066666666666667]

### confirmation-00032/BIND/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A second copy is stored at a separate location. Original documents are returned before public release. Contributors can remove private pages before publication.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00035/TRANSFER/2

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. No artist is given more display space than another. The artwork can be moved indoors when the weather turns. Artists are charged an identical amount to participate.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.38, 0.6066666666666667, 0.49333333333333335]

### confirmation-00009/NO_HISTORY/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. A professional curator checked the layout. A written load test supports the stand design. The installation team has relevant exhibition experience.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00011/BIND/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00026/NO_HISTORY/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Electrical items are disconnected before work begins. A replacement workspace is available if the main site closes. Visitors may decline a repair before any irreversible change.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00022/TRANSFER/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The workshop can move elsewhere if the usual venue becomes unavailable. The procedures were examined by a repair practitioner with recognized qualifications. People can refuse the repair before anything permanent is done.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.6066666666666667, 0.49333333333333335, 0.38]

### confirmation-00012/NEAR/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The arrangement was reviewed by someone who curates exhibitions professionally. Recorded testing provides evidence about the stands' ability to carry weight. The people installing the displays have done this kind of work before.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00018/NO_HISTORY/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A second copy is stored at a separate location. Original documents are returned before public release. Contributors can remove private pages before publication.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00000/BIND/2

Source: original_pilot. Status: valid. Raw output: '3'.
Selected message: Choose Plan A. Visitors receive the same appointment length. The contribution requested is identical for every visitor. Walk in priority rotates between the participating neighbourhoods.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00002/RANDOM_RESPONSE/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00032/NEAR/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. No contributing group receives a larger share of scanning capacity. The standards for submitting material do not depend on the contributor. Groups take turns occupying the first appointment.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00033/NEAR/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Work starts only after electrical equipment is unplugged. The workshop can move elsewhere if the usual venue becomes unavailable. People can refuse the repair before anything permanent is done.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00030/NO_HISTORY/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. No artist is given more display space than another. The artwork can be moved indoors when the weather turns. Artists are charged an identical amount to participate.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.38, 0.6066666666666667, 0.49333333333333335]

### confirmation-00013/RANDOM_RESPONSE/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00009/TRANSFER/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Recorded testing provides evidence about the stands' ability to carry weight. Different artists take turns occupying the most visible position. The people installing the displays have done this kind of work before.
Registered vector: [0.3333333333333333, 0.0, 0.6666666666666666]
P(A) for all three candidates: [0.38, 0.6066666666666667, 0.49333333333333335]

### confirmation-00011/NEAR/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The artwork can be moved indoors when the weather turns. The stands are fixed in place so they do not topple. Pulling out before installation does not cost an artist the entry payment.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00012/NO_HISTORY/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A professional curator checked the layout. A written load test supports the stand design. The installation team has relevant exhibition experience.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00024/TRANSFER/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The stands are fixed in place so they do not topple. The arrangement was reviewed by someone who curates exhibitions professionally. Pulling out before installation does not cost an artist the entry payment.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.49333333333333335, 0.38, 0.6066666666666667]

### confirmation-00031/TRANSFER/2

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The source documents go back to their owners before anything is released. The process was checked by an archivist with relevant qualifications. Sensitive pages can be taken out before they become public.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.38, 0.6066666666666667, 0.49333333333333335]

### confirmation-00023/RANDOM_RESPONSE/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A professional curator checked the layout. A written load test supports the stand design. The installation team has relevant exhibition experience.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00035/RANDOM_RESPONSE/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00034/NO_HISTORY/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Covered storage is available if rain interrupts the event. Display stands are secured against falling. Artists can withdraw before setup without losing their fee.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00001/NO_HISTORY/0

Source: original_pilot. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Each contributing group receives the same scanning quota. All contributors face identical submission rules. The first scanning appointment rotates between groups.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00005/NO_HISTORY/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The workshop can move elsewhere if the usual venue becomes unavailable. The procedures were examined by a repair practitioner with recognized qualifications. People can refuse the repair before anything permanent is done.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.49333333333333335, 0.6066666666666667, 0.38]

### confirmation-00033/TRANSFER/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The workshop can move elsewhere if the usual venue becomes unavailable. The procedures were examined by a repair practitioner with recognized qualifications. People can refuse the repair before anything permanent is done.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.38, 0.6066666666666667, 0.49333333333333335]

### confirmation-00025/TRANSFER/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. No contributing group receives a larger share of scanning capacity. A copy elsewhere protects the files if one location is lost. The standards for submitting material do not depend on the contributor.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.6066666666666667, 0.38, 0.49333333333333335]

### confirmation-00005/BIND/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00014/BIND/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00032/NO_HISTORY/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A second copy is stored at a separate location. Original documents are returned before public release. Contributors can remove private pages before publication.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00021/BIND/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Visitors receive the same appointment length. The contribution requested is identical for every visitor. Walk in priority rotates between the participating neighbourhoods.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00006/RANDOM_RESPONSE/2

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. A professional curator checked the layout. A written load test supports the stand design. The installation team has relevant exhibition experience.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00001/NO_HISTORY/3

Source: original_pilot. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. No contributing group receives a larger share of scanning capacity. A copy elsewhere protects the files if one location is lost. The standards for submitting material do not depend on the contributor.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.38, 0.6066666666666667, 0.49333333333333335]

### confirmation-00031/BIND/1

Source: extension. Status: valid. Raw output: '3'.
Selected message: Choose Plan A. Each contributing group receives the same scanning quota. All contributors face identical submission rules. The first scanning appointment rotates between groups.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00019/NEAR/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. No artist is given more display space than another. Artists are charged an identical amount to participate. Different artists take turns occupying the most visible position.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00026/TRANSFER/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The workshop can move elsewhere if the usual venue becomes unavailable. The procedures were examined by a repair practitioner with recognized qualifications. People can refuse the repair before anything permanent is done.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.38, 0.49333333333333335, 0.6066666666666667]

### confirmation-00013/NO_HISTORY/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Covered storage is available if rain interrupts the event. Display stands are secured against falling. Artists can withdraw before setup without losing their fee.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00002/NO_HISTORY/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. There is a written record of the trial of this process. The neighbourhoods take turns having first access to walk in places. The people doing the work have been instructed in those particular jobs.
Registered vector: [0.3333333333333333, 0.0, 0.6666666666666666]
P(A) for all three candidates: [0.38, 0.49333333333333335, 0.6066666666666667]

### confirmation-00006/BIND/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00010/RANDOM_RESPONSE/2

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Covered storage is available if rain interrupts the event. Display stands are secured against falling. Artists can withdraw before setup without losing their fee.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00011/BIND/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00018/NEAR/1

Source: extension. Status: valid. Raw output: '3'.
Selected message: Choose Plan A. The process was checked by an archivist with relevant qualifications. A documented inspection of sample images confirmed that they could be read. The staff handling delicate papers have received appropriate instruction.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00007/RANDOM_RESPONSE/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00012/RANDOM_RESPONSE/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A professional curator checked the layout. A written load test supports the stand design. The installation team has relevant exhibition experience.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00029/BIND/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A qualified archivist reviewed the procedure. A recorded sample check verified image readability. Staff were trained to handle fragile documents.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00029/TRANSFER/2

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. No contributing group receives a larger share of scanning capacity. A copy elsewhere protects the files if one location is lost. The standards for submitting material do not depend on the contributor.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.6066666666666667, 0.38, 0.49333333333333335]

### confirmation-00031/RANDOM_RESPONSE/2

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. A second copy is stored at a separate location. Original documents are returned before public release. Contributors can remove private pages before publication.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00017/BIND/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A professional curator checked the layout. A written load test supports the stand design. The installation team has relevant exhibition experience.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00012/BIND/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A professional curator checked the layout. A written load test supports the stand design. The installation team has relevant exhibition experience.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00028/TRANSFER/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. No artist is given more display space than another. The artwork can be moved indoors when the weather turns. Artists are charged an identical amount to participate.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.49333333333333335, 0.6066666666666667, 0.38]

### confirmation-00020/BIND/1

Source: extension. Status: valid. Raw output: '3'.
Selected message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00026/RANDOM_RESPONSE/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00033/NEAR/2

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Work starts only after electrical equipment is unplugged. The workshop can move elsewhere if the usual venue becomes unavailable. People can refuse the repair before anything permanent is done.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00020/RANDOM_RESPONSE/0

Source: extension. Status: valid. Raw output: '3'.
Selected message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00032/NO_HISTORY/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The source documents go back to their owners before anything is released. The process was checked by an archivist with relevant qualifications. Sensitive pages can be taken out before they become public.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.6066666666666667, 0.49333333333333335, 0.38]

### confirmation-00017/TRANSFER/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. No artist is given more display space than another. The artwork can be moved indoors when the weather turns. Artists are charged an identical amount to participate.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.49333333333333335, 0.6066666666666667, 0.38]

### confirmation-00001/NEAR/1

Source: original_pilot. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The process was checked by an archivist with relevant qualifications. A documented inspection of sample images confirmed that they could be read. The staff handling delicate papers have received appropriate instruction.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00012/RANDOM_RESPONSE/1

Source: extension. Status: valid. Raw output: '3'.
Selected message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00017/RANDOM_RESPONSE/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A professional curator checked the layout. A written load test supports the stand design. The installation team has relevant exhibition experience.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00031/TRANSFER/3

Source: extension. Status: valid. Raw output: '3'.
Selected message: Choose Plan A. No contributing group receives a larger share of scanning capacity. A copy elsewhere protects the files if one location is lost. The standards for submitting material do not depend on the contributor.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.49333333333333335, 0.38, 0.6066666666666667]

### confirmation-00025/BIND/2

Source: extension. Status: valid. Raw output: '3'.
Selected message: Choose Plan A. A qualified archivist reviewed the procedure. A recorded sample check verified image readability. Staff were trained to handle fragile documents.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00035/RANDOM_RESPONSE/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00017/BIND/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A professional curator checked the layout. A written load test supports the stand design. The installation team has relevant exhibition experience.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00017/RANDOM_RESPONSE/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A professional curator checked the layout. A written load test supports the stand design. The installation team has relevant exhibition experience.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00016/NEAR/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The procedures were examined by a repair practitioner with recognized qualifications. There is a written record of the trial of this process. The people doing the work have been instructed in those particular jobs.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00021/RANDOM_RESPONSE/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Visitors receive the same appointment length. The contribution requested is identical for every visitor. Walk in priority rotates between the participating neighbourhoods.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00024/RANDOM_RESPONSE/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00011/NEAR/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. No artist is given more display space than another. Artists are charged an identical amount to participate. Different artists take turns occupying the most visible position.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00025/NO_HISTORY/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The source documents go back to their owners before anything is released. The process was checked by an archivist with relevant qualifications. Sensitive pages can be taken out before they become public.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.38, 0.49333333333333335, 0.6066666666666667]

### confirmation-00014/RANDOM_RESPONSE/2

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00026/NEAR/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The procedures were examined by a repair practitioner with recognized qualifications. There is a written record of the trial of this process. The people doing the work have been instructed in those particular jobs.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00001/TRANSFER/3

Source: original_pilot. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. A documented inspection of sample images confirmed that they could be read. Groups take turns occupying the first appointment. The staff handling delicate papers have received appropriate instruction.
Registered vector: [0.3333333333333333, 0.0, 0.6666666666666666]
P(A) for all three candidates: [0.49333333333333335, 0.38, 0.6066666666666667]

### confirmation-00025/NEAR/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. No contributing group receives a larger share of scanning capacity. The standards for submitting material do not depend on the contributor. Groups take turns occupying the first appointment.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00024/NEAR/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. No artist is given more display space than another. Artists are charged an identical amount to participate. Different artists take turns occupying the most visible position.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00015/TRANSFER/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. There is a written record of the trial of this process. The neighbourhoods take turns having first access to walk in places. The people doing the work have been instructed in those particular jobs.
Registered vector: [0.3333333333333333, 0.0, 0.6666666666666666]
P(A) for all three candidates: [0.6066666666666667, 0.49333333333333335, 0.38]

### confirmation-00009/BIND/2

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. A professional curator checked the layout. A written load test supports the stand design. The installation team has relevant exhibition experience.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00023/TRANSFER/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. No artist is given more display space than another. The artwork can be moved indoors when the weather turns. Artists are charged an identical amount to participate.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.38, 0.49333333333333335, 0.6066666666666667]

### confirmation-00029/NO_HISTORY/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A qualified archivist reviewed the procedure. A recorded sample check verified image readability. Staff were trained to handle fragile documents.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00029/RANDOM_RESPONSE/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A qualified archivist reviewed the procedure. A recorded sample check verified image readability. Staff were trained to handle fragile documents.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00024/NO_HISTORY/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The stands are fixed in place so they do not topple. The arrangement was reviewed by someone who curates exhibitions professionally. Pulling out before installation does not cost an artist the entry payment.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.38, 0.6066666666666667, 0.49333333333333335]

### confirmation-00025/RANDOM_RESPONSE/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Each contributing group receives the same scanning quota. All contributors face identical submission rules. The first scanning appointment rotates between groups.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00030/RANDOM_RESPONSE/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00019/RANDOM_RESPONSE/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00017/BIND/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00025/TRANSFER/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The source documents go back to their owners before anything is released. The process was checked by an archivist with relevant qualifications. Sensitive pages can be taken out before they become public.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.6066666666666667, 0.38, 0.49333333333333335]

### confirmation-00010/TRANSFER/2

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The stands are fixed in place so they do not topple. The arrangement was reviewed by someone who curates exhibitions professionally. Pulling out before installation does not cost an artist the entry payment.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.38, 0.6066666666666667, 0.49333333333333335]

### confirmation-00024/NO_HISTORY/1

Source: extension. Status: valid. Raw output: '3'.
Selected message: Choose Plan A. A professional curator checked the layout. A written load test supports the stand design. The installation team has relevant exhibition experience.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00027/BIND/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Visitors receive the same appointment length. The contribution requested is identical for every visitor. Walk in priority rotates between the participating neighbourhoods.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00010/NO_HISTORY/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Recorded testing provides evidence about the stands' ability to carry weight. Different artists take turns occupying the most visible position. The people installing the displays have done this kind of work before.
Registered vector: [0.3333333333333333, 0.0, 0.6666666666666666]
P(A) for all three candidates: [0.38, 0.6066666666666667, 0.49333333333333335]

### confirmation-00027/RANDOM_RESPONSE/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00035/BIND/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00016/RANDOM_RESPONSE/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00031/RANDOM_RESPONSE/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A qualified archivist reviewed the procedure. A recorded sample check verified image readability. Staff were trained to handle fragile documents.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00017/NEAR/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. No artist is given more display space than another. Artists are charged an identical amount to participate. Different artists take turns occupying the most visible position.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00003/TRANSFER/0

Source: original_pilot. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. No artist is given more display space than another. The artwork can be moved indoors when the weather turns. Artists are charged an identical amount to participate.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.49333333333333335, 0.38, 0.6066666666666667]

### confirmation-00007/TRANSFER/2

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. There is a written record of the trial of this process. The neighbourhoods take turns having first access to walk in places. The people doing the work have been instructed in those particular jobs.
Registered vector: [0.3333333333333333, 0.0, 0.6666666666666666]
P(A) for all three candidates: [0.6066666666666667, 0.49333333333333335, 0.38]

### confirmation-00010/RANDOM_RESPONSE/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A professional curator checked the layout. A written load test supports the stand design. The installation team has relevant exhibition experience.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00001/NO_HISTORY/1

Source: original_pilot. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Each contributing group receives the same scanning quota. All contributors face identical submission rules. The first scanning appointment rotates between groups.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00024/RANDOM_RESPONSE/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Covered storage is available if rain interrupts the event. Display stands are secured against falling. Artists can withdraw before setup without losing their fee.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00000/RANDOM_RESPONSE/0

Source: original_pilot. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Electrical items are disconnected before work begins. A replacement workspace is available if the main site closes. Visitors may decline a repair before any irreversible change.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00016/NO_HISTORY/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. There is a written record of the trial of this process. The neighbourhoods take turns having first access to walk in places. The people doing the work have been instructed in those particular jobs.
Registered vector: [0.3333333333333333, 0.0, 0.6666666666666666]
P(A) for all three candidates: [0.6066666666666667, 0.38, 0.49333333333333335]

### confirmation-00033/TRANSFER/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The workshop can move elsewhere if the usual venue becomes unavailable. The procedures were examined by a repair practitioner with recognized qualifications. People can refuse the repair before anything permanent is done.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.6066666666666667, 0.49333333333333335, 0.38]

### confirmation-00006/NEAR/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. No artist is given more display space than another. Artists are charged an identical amount to participate. Different artists take turns occupying the most visible position.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00014/TRANSFER/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. There is a written record of the trial of this process. The neighbourhoods take turns having first access to walk in places. The people doing the work have been instructed in those particular jobs.
Registered vector: [0.3333333333333333, 0.0, 0.6666666666666666]
P(A) for all three candidates: [0.6066666666666667, 0.38, 0.49333333333333335]

### confirmation-00035/NEAR/2

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. No artist is given more display space than another. Artists are charged an identical amount to participate. Different artists take turns occupying the most visible position.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00004/BIND/2

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Electrical items are disconnected before work begins. A replacement workspace is available if the main site closes. Visitors may decline a repair before any irreversible change.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00035/TRANSFER/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. No artist is given more display space than another. The artwork can be moved indoors when the weather turns. Artists are charged an identical amount to participate.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.38, 0.6066666666666667, 0.49333333333333335]

### confirmation-00025/NEAR/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. No contributing group receives a larger share of scanning capacity. The standards for submitting material do not depend on the contributor. Groups take turns occupying the first appointment.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00015/TRANSFER/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Each visitor is offered an equal amount of appointment time. Work starts only after electrical equipment is unplugged. Nobody is asked to contribute more than another visitor.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.49333333333333335, 0.38, 0.6066666666666667]

### confirmation-00018/NO_HISTORY/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The source documents go back to their owners before anything is released. The process was checked by an archivist with relevant qualifications. Sensitive pages can be taken out before they become public.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.6066666666666667, 0.49333333333333335, 0.38]

### confirmation-00004/TRANSFER/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Each visitor is offered an equal amount of appointment time. Work starts only after electrical equipment is unplugged. Nobody is asked to contribute more than another visitor.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.49333333333333335, 0.6066666666666667, 0.38]

### confirmation-00004/TRANSFER/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Each visitor is offered an equal amount of appointment time. Work starts only after electrical equipment is unplugged. Nobody is asked to contribute more than another visitor.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.38, 0.49333333333333335, 0.6066666666666667]

### confirmation-00026/TRANSFER/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The workshop can move elsewhere if the usual venue becomes unavailable. The procedures were examined by a repair practitioner with recognized qualifications. People can refuse the repair before anything permanent is done.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.38, 0.49333333333333335, 0.6066666666666667]

### confirmation-00004/BIND/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Visitors receive the same appointment length. The contribution requested is identical for every visitor. Walk in priority rotates between the participating neighbourhoods.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00007/NEAR/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The procedures were examined by a repair practitioner with recognized qualifications. There is a written record of the trial of this process. The people doing the work have been instructed in those particular jobs.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00008/TRANSFER/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The source documents go back to their owners before anything is released. The process was checked by an archivist with relevant qualifications. Sensitive pages can be taken out before they become public.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.49333333333333335, 0.38, 0.6066666666666667]

### confirmation-00030/NEAR/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. No artist is given more display space than another. Artists are charged an identical amount to participate. Different artists take turns occupying the most visible position.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00031/NEAR/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The process was checked by an archivist with relevant qualifications. A documented inspection of sample images confirmed that they could be read. The staff handling delicate papers have received appropriate instruction.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00019/NO_HISTORY/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Covered storage is available if rain interrupts the event. Display stands are secured against falling. Artists can withdraw before setup without losing their fee.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00004/NO_HISTORY/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Visitors receive the same appointment length. The contribution requested is identical for every visitor. Walk in priority rotates between the participating neighbourhoods.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00011/TRANSFER/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The stands are fixed in place so they do not topple. The arrangement was reviewed by someone who curates exhibitions professionally. Pulling out before installation does not cost an artist the entry payment.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.6066666666666667, 0.38, 0.49333333333333335]

### confirmation-00000/RANDOM_RESPONSE/1

Source: original_pilot. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00022/NEAR/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The procedures were examined by a repair practitioner with recognized qualifications. There is a written record of the trial of this process. The people doing the work have been instructed in those particular jobs.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00014/NO_HISTORY/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. An accredited repair specialist reviewed the procedures. A documented practice session tested the workflow. The volunteers completed training for their assigned tasks.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00016/BIND/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Visitors receive the same appointment length. The contribution requested is identical for every visitor. Walk in priority rotates between the participating neighbourhoods.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00018/TRANSFER/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The source documents go back to their owners before anything is released. The process was checked by an archivist with relevant qualifications. Sensitive pages can be taken out before they become public.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.6066666666666667, 0.49333333333333335, 0.38]

### confirmation-00012/NO_HISTORY/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A professional curator checked the layout. A written load test supports the stand design. The installation team has relevant exhibition experience.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00015/NEAR/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The procedures were examined by a repair practitioner with recognized qualifications. There is a written record of the trial of this process. The people doing the work have been instructed in those particular jobs.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00034/NEAR/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The arrangement was reviewed by someone who curates exhibitions professionally. Recorded testing provides evidence about the stands' ability to carry weight. The people installing the displays have done this kind of work before.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00019/BIND/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00005/TRANSFER/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The workshop can move elsewhere if the usual venue becomes unavailable. The procedures were examined by a repair practitioner with recognized qualifications. People can refuse the repair before anything permanent is done.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.6066666666666667, 0.38, 0.49333333333333335]

### confirmation-00027/NO_HISTORY/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. There is a written record of the trial of this process. The neighbourhoods take turns having first access to walk in places. The people doing the work have been instructed in those particular jobs.
Registered vector: [0.3333333333333333, 0.0, 0.6666666666666666]
P(A) for all three candidates: [0.49333333333333335, 0.6066666666666667, 0.38]

### confirmation-00022/TRANSFER/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The workshop can move elsewhere if the usual venue becomes unavailable. The procedures were examined by a repair practitioner with recognized qualifications. People can refuse the repair before anything permanent is done.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.6066666666666667, 0.49333333333333335, 0.38]

### confirmation-00009/BIND/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. A professional curator checked the layout. A written load test supports the stand design. The installation team has relevant exhibition experience.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00001/NEAR/2

Source: original_pilot. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The process was checked by an archivist with relevant qualifications. A documented inspection of sample images confirmed that they could be read. The staff handling delicate papers have received appropriate instruction.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00007/NEAR/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The procedures were examined by a repair practitioner with recognized qualifications. There is a written record of the trial of this process. The people doing the work have been instructed in those particular jobs.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00018/RANDOM_RESPONSE/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A second copy is stored at a separate location. Original documents are returned before public release. Contributors can remove private pages before publication.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00012/NO_HISTORY/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Recorded testing provides evidence about the stands' ability to carry weight. Different artists take turns occupying the most visible position. The people installing the displays have done this kind of work before.
Registered vector: [0.3333333333333333, 0.0, 0.6666666666666666]
P(A) for all three candidates: [0.38, 0.6066666666666667, 0.49333333333333335]

### confirmation-00001/NEAR/0

Source: original_pilot. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The process was checked by an archivist with relevant qualifications. A documented inspection of sample images confirmed that they could be read. The staff handling delicate papers have received appropriate instruction.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00022/NEAR/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The procedures were examined by a repair practitioner with recognized qualifications. There is a written record of the trial of this process. The people doing the work have been instructed in those particular jobs.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00021/TRANSFER/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Each visitor is offered an equal amount of appointment time. Work starts only after electrical equipment is unplugged. Nobody is asked to contribute more than another visitor.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.38, 0.49333333333333335, 0.6066666666666667]

### confirmation-00000/NEAR/0

Source: original_pilot. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Work starts only after electrical equipment is unplugged. The workshop can move elsewhere if the usual venue becomes unavailable. People can refuse the repair before anything permanent is done.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00006/NO_HISTORY/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. No artist is given more display space than another. The artwork can be moved indoors when the weather turns. Artists are charged an identical amount to participate.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.6066666666666667, 0.49333333333333335, 0.38]

### confirmation-00027/TRANSFER/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. There is a written record of the trial of this process. The neighbourhoods take turns having first access to walk in places. The people doing the work have been instructed in those particular jobs.
Registered vector: [0.3333333333333333, 0.0, 0.6666666666666666]
P(A) for all three candidates: [0.6066666666666667, 0.38, 0.49333333333333335]

### confirmation-00021/TRANSFER/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Each visitor is offered an equal amount of appointment time. Work starts only after electrical equipment is unplugged. Nobody is asked to contribute more than another visitor.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.49333333333333335, 0.6066666666666667, 0.38]

### confirmation-00023/NEAR/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The arrangement was reviewed by someone who curates exhibitions professionally. Recorded testing provides evidence about the stands' ability to carry weight. The people installing the displays have done this kind of work before.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00004/NEAR/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Work starts only after electrical equipment is unplugged. The workshop can move elsewhere if the usual venue becomes unavailable. People can refuse the repair before anything permanent is done.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00014/NO_HISTORY/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The workshop can move elsewhere if the usual venue becomes unavailable. The procedures were examined by a repair practitioner with recognized qualifications. People can refuse the repair before anything permanent is done.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.6066666666666667, 0.38, 0.49333333333333335]

### confirmation-00011/RANDOM_RESPONSE/2

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Covered storage is available if rain interrupts the event. Display stands are secured against falling. Artists can withdraw before setup without losing their fee.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00025/NO_HISTORY/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Each contributing group receives the same scanning quota. All contributors face identical submission rules. The first scanning appointment rotates between groups.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00011/RANDOM_RESPONSE/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Covered storage is available if rain interrupts the event. Display stands are secured against falling. Artists can withdraw before setup without losing their fee.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00034/RANDOM_RESPONSE/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. A professional curator checked the layout. A written load test supports the stand design. The installation team has relevant exhibition experience.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00010/NEAR/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The arrangement was reviewed by someone who curates exhibitions professionally. Recorded testing provides evidence about the stands' ability to carry weight. The people installing the displays have done this kind of work before.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00035/NEAR/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. No artist is given more display space than another. Artists are charged an identical amount to participate. Different artists take turns occupying the most visible position.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00023/NEAR/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. No artist is given more display space than another. Artists are charged an identical amount to participate. Different artists take turns occupying the most visible position.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00033/NO_HISTORY/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. There is a written record of the trial of this process. The neighbourhoods take turns having first access to walk in places. The people doing the work have been instructed in those particular jobs.
Registered vector: [0.3333333333333333, 0.0, 0.6666666666666666]
P(A) for all three candidates: [0.38, 0.6066666666666667, 0.49333333333333335]

### confirmation-00009/RANDOM_RESPONSE/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00003/TRANSFER/1

Source: original_pilot. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. No artist is given more display space than another. The artwork can be moved indoors when the weather turns. Artists are charged an identical amount to participate.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.38, 0.6066666666666667, 0.49333333333333335]

### confirmation-00032/NO_HISTORY/0

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A second copy is stored at a separate location. Original documents are returned before public release. Contributors can remove private pages before publication.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00027/RANDOM_RESPONSE/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Visitors receive the same appointment length. The contribution requested is identical for every visitor. Walk in priority rotates between the participating neighbourhoods.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00006/NO_HISTORY/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. No artist is given more display space than another. The artwork can be moved indoors when the weather turns. Artists are charged an identical amount to participate.
Registered vector: [0.6666666666666666, 0.3333333333333333, 0.0]
P(A) for all three candidates: [0.49333333333333335, 0.38, 0.6066666666666667]

### confirmation-00032/NEAR/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. No contributing group receives a larger share of scanning capacity. The standards for submitting material do not depend on the contributor. Groups take turns occupying the first appointment.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00004/NEAR/1

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Work starts only after electrical equipment is unplugged. The workshop can move elsewhere if the usual venue becomes unavailable. People can refuse the repair before anything permanent is done.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.38, 0.38, 0.72]

### confirmation-00027/BIND/2

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Visitors receive the same appointment length. The contribution requested is identical for every visitor. Walk in priority rotates between the participating neighbourhoods.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00001/RANDOM_RESPONSE/0

Source: original_pilot. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. A qualified archivist reviewed the procedure. A recorded sample check verified image readability. Staff were trained to handle fragile documents.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00020/NEAR/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The arrangement was reviewed by someone who curates exhibitions professionally. Recorded testing provides evidence about the stands' ability to carry weight. The people installing the displays have done this kind of work before.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.72, 0.38, 0.38]

### confirmation-00017/NO_HISTORY/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Recorded testing provides evidence about the stands' ability to carry weight. Different artists take turns occupying the most visible position. The people installing the displays have done this kind of work before.
Registered vector: [0.3333333333333333, 0.0, 0.6666666666666666]
P(A) for all three candidates: [0.6066666666666667, 0.38, 0.49333333333333335]

### confirmation-00000/TRANSFER/1

Source: original_pilot. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The workshop can move elsewhere if the usual venue becomes unavailable. The procedures were examined by a repair practitioner with recognized qualifications. People can refuse the repair before anything permanent is done.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.6066666666666667, 0.38, 0.49333333333333335]

### confirmation-00026/NEAR/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The procedures were examined by a repair practitioner with recognized qualifications. There is a written record of the trial of this process. The people doing the work have been instructed in those particular jobs.
Registered vector: [0.0, 0.0, 1.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00008/TRANSFER/2

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The source documents go back to their owners before anything is released. The process was checked by an archivist with relevant qualifications. Sensitive pages can be taken out before they become public.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.6066666666666667, 0.49333333333333335, 0.38]

### confirmation-00014/TRANSFER/1

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. The workshop can move elsewhere if the usual venue becomes unavailable. The procedures were examined by a repair practitioner with recognized qualifications. People can refuse the repair before anything permanent is done.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.49333333333333335, 0.6066666666666667, 0.38]

### confirmation-00009/RANDOM_RESPONSE/2

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. Every artist receives an equally sized display area. The entry fee is the same for all artists. The prominent display position rotates during the event.
Registered vector: [1.0, 0.0, 0.0]
P(A) for all three candidates: [0.5, 0.5, 0.5]

### confirmation-00010/TRANSFER/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The stands are fixed in place so they do not topple. The arrangement was reviewed by someone who curates exhibitions professionally. Pulling out before installation does not cost an artist the entry payment.
Registered vector: [0.0, 0.6666666666666666, 0.3333333333333333]
P(A) for all three candidates: [0.6066666666666667, 0.49333333333333335, 0.38]

### confirmation-00013/BIND/3

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. Covered storage is available if rain interrupts the event. Display stands are secured against falling. Artists can withdraw before setup without losing their fee.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]

### confirmation-00008/NO_HISTORY/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A documented inspection of sample images confirmed that they could be read. Groups take turns occupying the first appointment. The staff handling delicate papers have received appropriate instruction.
Registered vector: [0.3333333333333333, 0.0, 0.6666666666666666]
P(A) for all three candidates: [0.6066666666666667, 0.49333333333333335, 0.38]

### confirmation-00008/TRANSFER/3

Source: extension. Status: valid. Raw output: '1'.
Selected message: Choose Plan A. A documented inspection of sample images confirmed that they could be read. Groups take turns occupying the first appointment. The staff handling delicate papers have received appropriate instruction.
Registered vector: [0.3333333333333333, 0.0, 0.6666666666666666]
P(A) for all three candidates: [0.49333333333333335, 0.38, 0.6066666666666667]

### confirmation-00013/NEAR/0

Source: extension. Status: valid. Raw output: '2'.
Selected message: Choose Plan A. The artwork can be moved indoors when the weather turns. The stands are fixed in place so they do not topple. Pulling out before installation does not cost an artist the entry payment.
Registered vector: [0.0, 1.0, 0.0]
P(A) for all three candidates: [0.38, 0.72, 0.38]
