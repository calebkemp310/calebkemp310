# Trading agent

Research and, if a strategy ever passes validation, a 24/7 crypto trading agent with hard-coded risk limits.

Start with [SPEC.md](SPEC.md). Gate 1 result: no strategy passed, nothing is deployed, and no code here can place an order.

```
pip install -r requirements.txt
python -m pytest -q
python -m research.run_research   # writes results/research.md
```
