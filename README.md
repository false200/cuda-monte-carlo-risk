# GPU Monte Carlo Risk Engine

Custom CUDA kernels price a synthetic book of equities and European options, revalue that book under correlated geometric Brownian motion, and return Value-at-Risk and expected shortfall. No model is trained. Default demo size is **10 million** scenarios (presets: 1M / 10M / 100M).

The longer method write-up is in [architecture.md](architecture.md). A slide-ready Batch diagram is in [docs/aws-path-architecture.png](docs/aws-path-architecture.png) (proposed path only).

## Architecture (what is live)

### Live path (deployed)

One GPU EC2 instance runs the whole app in Docker. ECR, Lambda, API Gateway, and Batch are **not** used in this path.

```text
Browser
  -> http://<ec2-public-ip>:8765
  -> Docker on EC2 g4dn.xlarge (Tesla T4)
       dashboard/server.py  (MC_HOST=0.0.0.0)
       -> /opt/mc_engine + kernels/mc_risk.cu  (NVRTC)
       -> GPU
  -> result JSON back to the page
```

How that instance was brought up:

1. Copy this repo onto the EC2 box.
2. `docker build -f docker/Dockerfile -t mc-risk .` **on the instance** (image stays in local Docker; not pushed to ECR).
3. `docker run --gpus all -p 8765:8765 ...` with the dashboard entrypoint.
4. Open the public URL on port **8765**.

The dashboard draws a new synthetic book from `GET /api/random` on every Run click (and on first load) and prices that book. The fixed example in `GET /api/sample` is unchanged. The scenario count stays on the preset you picked.

### Local path (measured results)

```text
Browser -> dashboard/server.py on 127.0.0.1:8765 -> build/mc_engine -> workstation GPU
```

Timed figures in this README are from an RTX 3050 Laptop unless noted.

### Proposed path (source only, not deployed)

`aws/` + `docker/` describe API Gateway → Lambda (validate / enqueue, **no CUDA**) → S3 → Batch spot `g4dn`/`g5` → ECR image with the same `mc_engine`. That SAM stack was **not** deployed. The live demo is the single EC2 + Docker path above.

## Synthetic dataset

The sample portfolio is synthetic. Spots, volatilities, dividends, rates, drifts, correlation, and positions are constants in `sample_portfolio()` in `common/jobtext.py`. Nothing was downloaded from an exchange, a data vendor, or a historical file. Nothing was fitted or trained. The labels SPX, AAPL, XOM, and GLD are names only. The numbers are not live quotes.

| Name | Spot | Volatility | Dividend |
| --- | --- | --- | --- |
| SPX | 5,200 | 16% | 1.3% |
| AAPL | 190 | 28% | 0.5% |
| XOM | 110 | 22% | 3.2% |
| GLD | 180 | 14% | 0% |

The rate on every name is 4.5%. Drift is rate minus dividend. Seed is 42. Default `paths` is **10,000,000**. Positions are long 8 SPX, short 4 SPX 5000 puts, long 30 AAPL 200 calls and 20 AAPL 170 puts, long 40 XOM and 25 GLD, plus one synthetic AAPL Asian.

## What the engine does

- Hand-written CUDA in `kernels/mc_risk.cu`. No cuRAND, no vendor pricer.
- Philox4x32-10, checked against published test vectors on CPU and GPU.
- European prices use antithetic variates and are checked against Black-Scholes.
- Portfolio scenarios use a Cholesky factor, then a full revaluation. VaR and ES come from a GPU 4096-bin histogram.
- One arithmetic Asian uses a geometric Asian control variate.
- A multi-threaded CPU baseline reports the speedup.
- Host compiles kernels at runtime with **NVRTC** (cubin/PTX cache beside the binary).

## Requirements

| Tool | Used for |
| --- | --- |
| 64-bit MinGW-w64 `gcc` | Windows host build. Set `CC` if it is not on `PATH`. |
| Python 3.9 or newer | Dashboard and job validation. |
| NVIDIA driver and GPU | Local or EC2 GPU runs. |
| Docker + NVIDIA Container Toolkit | EC2 live demo image. |

## Quick start (local Windows)

```powershell
powershell -File .\build.ps1
powershell -File .\run_dashboard.ps1
```

Open http://127.0.0.1:8765.

```powershell
.\build\mc_engine.exe selftest
.\build\mc_engine.exe run .\path\to\job.txt .\path\to\result.json
```

## EC2 + Docker (live style)

On a Deep Learning GPU AMI (`g4dn.xlarge` or similar), after the repo is on the box:

```bash
cd ~/HPC_L2
sudo docker build -f docker/Dockerfile -t mc-risk .
sudo docker run -d --name mc-risk --gpus all -p 8765:8765 --restart unless-stopped \
  -e MC_HOST=0.0.0.0 -e MC_PORT=8765 -e MC_ENGINE=/opt/mc_engine \
  --entrypoint python3 mc-risk /opt/dashboard/server.py
```

Open `http://<public-ip>:8765`. Security group needs TCP **22** (SSH) and **8765** (dashboard).

| Variable | Meaning |
| --- | --- |
| `MC_HOST` | Bind address. Use `0.0.0.0` on EC2. Default `127.0.0.1`. |
| `MC_PORT` | HTTP port. Default `8765`. |
| `MC_ENGINE` | Path to `mc_engine` binary inside the container. |
| `MC_KERNEL` | Path to `mc_risk.cu`. |
| `NVRTC_PATH` | NVRTC library path. |

## Model

Prices follow geometric Brownian motion. One trading day is `1/252` of a year. Equities are marked at the simulated spot; options are Black-Scholes with remaining maturity. VaR is the loss at the 95% and 99% P&L quantiles. Expected shortfall is the average P&L inside that tail.

The dashboard cost column multiplies measured GPU seconds by published us-east-1 on-demand list rates (`g4dn.xlarge` / `g5.xlarge`). That column is an estimate, not a bill.

## Example results

Workstation reference: NVIDIA GeForce RTX 3050 Laptop.

| Check | Result |
| --- | --- |
| Black-Scholes ATM call, S = K = 100, r = 5%, vol = 20%, T = 1 | 10.450584, host and device agree |
| 100 million scenarios, 1-day horizon | portfolio value 50,699.92 |
| 95% / 99% VaR | 853.34 / 1,211.44 |
| 99% expected shortfall | 1,390.12 |
| GPU job time | 8.39 s |
| European pricing | ~278 million paths/s, about 8.5× a 12-thread CPU |
| Scenario revaluation | ~25.6 million paths/s |

A live smoke run on EC2 `g4dn.xlarge` (Tesla T4) completed a 1 million path book successfully with the same engine binary in Docker.

## Layout

| Path | Role |
| --- | --- |
| `architecture.md` | Method, kernels, synthetic book, measured local results |
| `kernels/mc_risk.cu` | RNG, European pricing, scenario VaR, Asian control variate |
| `src/engine.c` | Driver API host, CPU baseline, JSON writer |
| `dashboard/` | Browser UI and Python API |
| `common/jobtext.py` | Sample book, validation, job text format |
| `docker/` | Dockerfile, Batch entrypoint, dashboard serve helper |
| `aws/` | Lambda + SAM template for Batch. Designed, not deployed |
| `docs/` | Architecture diagrams for slides |
| `build.ps1` | Windows build and self-test |
