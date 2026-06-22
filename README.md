# Quantum Subset Sum Demo

Educational Qiskit demos for solving small Subset Sum instances with Grover's
algorithm.

The code and notebooks here focus on Subset Sum, not the older Sudoku demo that
used to live in this repository.

The core problem is:

Given positive integers $a_0, a_1, \ldots, a_{n-1}$ and a target integer $T$,
find $x$ in $\{0,1\}^n$ such that:

$$
\sum_i x_i a_i = T
$$

The selector bit `x_i` means whether the number `a_i` is included in the
subset. Grover search prepares a superposition over all selector bitstrings,
marks the bitstrings whose weighted sum equals the target, and amplifies the
marked states.

## Two Demo Tracks

This repository has two related but different demo tracks:

1. **High-level `WeightedAdder` demo**
   - Main file: `subset_sum_grover_weighted_adder.ipynb`
   - Uses Qiskit's `WeightedAdder` to compute the subset sum.
   - Best starting point for understanding the Grover workflow.
   - The arithmetic is correct but mostly hidden inside Qiskit's library.
   - It can be used to explain the code in `quantum_subset_sum_weighted_adder.py`.

2. **Based on the paper**
   - Main file: `subset_sum_grover_based_on_paper.ipynb`
   - Follows the outline of a lower-level construction from the referenced
     paper (https://arxiv.org/pdf/2410.01775).
   - Better for studying how the arithmetic/oracle might be built explicitly.
   - More exploratory and less polished than the `WeightedAdder` notebook. Note the paper already has it own repo at `ABenoit0226/quantum-place-route`.

The Python script is a reusable helper / smoke-test version of the
`WeightedAdder` approach. It is not the primary tutorial demo.

## Files

- `subset_sum_grover_weighted_adder.ipynb` - notebook using
  Qiskit's `WeightedAdder` to compute the weighted sum.
- `quantum_subset_sum_weighted_adder.py` - reusable Python implementation of
  the weighted-adder Grover approach.
- `subset_sum_grover_based_on_paper.ipynb` - notebook sketch following the
  procedure described in the paper at https://arxiv.org/pdf/2410.01775.
- `subset_sum_grover_demo.ipynb` - introductory Grover / subset-sum notebook.

## WeightedAdder Approach

For a set such as:

```python
S = [1, 2, 3]
target = 3
```

the valid selector bitstrings are:

```text
011 -> choose 1 and 2
100 -> choose 3
```

The weighted-adder Grover oracle follows this pattern:

```text
1. Put selector qubits into superposition.
2. Use WeightedAdder to compute sum_i x_i * a_i into a sum register.
3. Phase-flip states whose sum register equals target.
4. Uncompute the WeightedAdder so workspace qubits return to |0>.
5. Apply the Grover diffuser to selector qubits only.
6. Measure selector qubits and decode the subset.
```

The important reversible-computing step is uncomputation. The sum register and
adder work qubits must be cleared before the diffuser, otherwise the selector
qubits remain entangled with arithmetic workspace.

## Install

```bash
python -m pip install -r requirements.txt
```

## Run the Notebook Demos

Recommended starting point:

```bash
jupyter notebook subset_sum_grover_weighted_adder.ipynb
```

Notebook based on the paper:

```bash
jupyter notebook subset_sum_grover_based_on_paper.ipynb
```

Introductory notebook:

```bash
jupyter notebook subset_sum_grover_demo.ipynb
```

## Run the Python Helper

```bash
python quantum_subset_sum_weighted_adder.py
```

The script tries a few small examples and prints the result returned by
`quantum_subset_sum`. Treat this as a quick command-line check and reusable
implementation, not the main explanatory demo.

## Use the Helper Function

```python
from quantum_subset_sum_weighted_adder import quantum_subset_sum

result = quantum_subset_sum([1, 2, 3], 3, shots=2000, verbose=True)
print(result)
```

The result includes:

- the subset indices found
- the selector bits
- the total
- status, such as `found`, `found_by_classical_fallback`, or
  `no_solution_certified`
- the Grover iteration count when applicable

## Notes

This is a small bootcamp-style project. The `WeightedAdder` version is useful
for explaining the algorithm without hand-building the reversible arithmetic.
The notebook based on the paper is where we explore lower-level oracle
construction.

