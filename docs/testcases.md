"What's my flight status for Paris to Austin?"
"I need to change my seat"
"What's the baggage policy?"




## Test Questions

| Question | Expected Tool | Key Data |
|----------|---------------|----------|
| `What is the baggage policy?` | faq | Uses faq_data.py |
| `I want to book flight DA100 to Los Angeles` | book_flight | Flight DA100: JFK → LAX |
| `Cancel my booking IR-D204` | cancel_flight | Morgan Lee's disrupted Paris→Austin trip |