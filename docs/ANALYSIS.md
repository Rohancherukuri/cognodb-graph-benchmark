# Analysis

> **This file is a template.** Every bracketed `[...]` placeholder below
> should be replaced with real numbers pulled from `results/REPORT.md`
> after a live run against real accounts (`make dataset && make bench &&
> make report`). Do not fill in numbers you have not actually measured —
> the assignment weights honest, evidence-backed analysis over polish.

## TL;DR

- Fastest ingest: **[platform]** at **[X nodes/s, Y rels/s]**
- Lowest read latency (p95, 1-hop traversal): **[platform]** at **[X ms]**
- Best mixed-workload throughput at 40 concurrent clients: **[platform]**
  at **[X qps]**
- Biggest surprise: **[what and why]**

## Ingest

`[Summarize the ingest table. Which platform batches writes most
efficiently? Did any platform throttle under the free-tier resource cap —
and how do you know (error messages, timeouts, throughput cliffs)?]`

## Traversals (1 / 2 / 3 hop)

`[How does p95 latency grow with hop depth on each platform? Is the growth
roughly linear, or does one platform's query planner degrade faster? Note
whether any platform uses native graph traversal vs. relational-style joins
under the hood, and whether that shows up in the numbers.]`

## Lookups

`[Point lookup vs. indexed lookup - by how much does an index help on each
platform? Is any platform's "point lookup" actually already index-backed by
default (e.g. primary key lookup), making the comparison less meaningful -
call that out explicitly if so.]`

## Aggregation

`[What does the group-by/count query cost look like relative to a single
traversal? Does any platform have a specialized aggregation pipeline that
shows a clear advantage?]`

## Mixed workload / concurrency

`[How does QPS scale from 1 -> 10 -> 40 concurrent clients per platform?
Does any platform plateau or regress at higher concurrency (lock
contention, connection pool limits, single-threaded query execution)? Tie
this back to the 0.5 vCPU cap - a single core is the likely ceiling for
several of these platforms.]`

## Footprint

`[What could you actually observe? Be explicit about what was "not
observable" per platform and why (managed free tiers frequently don't
expose this over the client protocol).]`

## Root-cause reasoning

`[Where you can, explain *why* platforms differ - native graph storage vs.
graph-on-relational, index structures, protocol overhead (Bolt vs. HTTP vs.
gRPC), JIT/compiled query execution, etc. Speculation is fine if it's
labeled as speculation.]`

## Caveats and threats to validity

`[Pull directly from every platform's "caveats" list in the result JSON.
Also note anything not captured by the harness: network variance between
your machine and each region, free-tier cold-starts/scale-to-zero behavior,
etc.]`
