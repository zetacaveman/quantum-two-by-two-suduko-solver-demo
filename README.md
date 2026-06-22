# QuantumSubsetSumSolver

Educational Qiskit demos for solving small Subset Sum instances with Grover's
algorithm.

This repository is currently being prepared to move from an older Sudoku-demo
name to `QuantumSubsetSumSolver`. The code and notebooks here now focus on
Subset Sum, not Sudoku.

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

## Run the Python Demo

```bash
python quantum_subset_sum_weighted_adder.py
```

The script tries a few small examples and prints the result returned by
`quantum_subset_sum`.

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
The notebook based on the paper is a better place to explore lower-level oracle
construction.

The paper authors also provide a public repository with relevant code:
`ABenoit0226/quantum-place-route`. This project is only an educational
exploration of the steps and does not claim originality over that work.
