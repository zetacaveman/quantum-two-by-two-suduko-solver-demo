from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from math import ceil, pi, sqrt

from qiskit import ClassicalRegister, QuantumCircuit, transpile
from qiskit.circuit.library import WeightedAdder
from qiskit_aer import AerSimulator


@dataclass(frozen=True)
class SubsetSumResult:
    """Result returned by quantum_subset_sum."""

    subset: set[int] | None
    bits: tuple[int, ...] | None
    total: int | None
    status: str
    grover_iterations: int | None = None
    shots: int = 0


def little_endian_bits(value: int, width: int) -> list[int]:
    """Return bits as [bit_0, bit_1, ..., bit_{width-1}]."""
    return [(value >> j) & 1 for j in range(width)]


def phase_flip_on_sum_equal_target(
    qc: QuantumCircuit,
    sum_qubits: list[int],
    target: int,
) -> None:
    """Apply a phase -1 exactly when the sum register equals target."""
    target_bits = little_endian_bits(target, len(sum_qubits))

    # Convert the target pattern to all ones.
    for qubit, bit in zip(sum_qubits, target_bits):
        if bit == 0:
            qc.x(qubit)

    # Phase flip |11...1>.
    if len(sum_qubits) == 1:
        qc.z(sum_qubits[0])
    else:
        qc.mcp(pi, sum_qubits[:-1], sum_qubits[-1])

    # Undo the conversion.
    for qubit, bit in zip(sum_qubits, target_bits):
        if bit == 0:
            qc.x(qubit)


def subset_sum_oracle_weighted_adder(xs: list[int], target: int) -> QuantumCircuit:
    """
    Build the subset-sum phase oracle.

    The oracle applies

        |b> -> -|b>  if sum_i b_i xs[i] == target
        |b> ->  |b>  otherwise

    It uses Qiskit's WeightedAdder to compute the weighted sum into a sum
    register, marks the target sum by phase, and then uncomputes the sum.
    """
    n = len(xs)
    weights = [int(x) for x in xs]
    adder = WeightedAdder(num_state_qubits=n, weights=weights)
    qc = QuantumCircuit(adder.num_qubits, name="SubsetSumOracle")
    all_qubits = list(range(adder.num_qubits))

    qc.append(adder.to_gate(), all_qubits)

    # WeightedAdder layout: state qubits first, then sum qubits, then helpers.
    sum_start = n
    sum_qubits = list(range(sum_start, sum_start + adder.num_sum_qubits))
    phase_flip_on_sum_equal_target(qc, sum_qubits, target)

    qc.append(adder.inverse().to_gate(), all_qubits)
    return qc


def diffusion_operator(n: int, total_qubits: int) -> QuantumCircuit:
    """Grover diffusion over only the first n selector qubits."""
    qc = QuantumCircuit(total_qubits, name="Diffusion")
    selector = list(range(n))

    qc.h(selector)
    qc.x(selector)

    if n == 1:
        qc.z(selector[0])
    else:
        qc.h(selector[-1])
        qc.mcx(selector[:-1], selector[-1])
        qc.h(selector[-1])

    qc.x(selector)
    qc.h(selector)

    return qc


def decode_qiskit_key(key: str, n: int) -> tuple[int, ...]:
    """
    Convert Qiskit's displayed count key into selector-bit order.

    We measure selector qubit i into classical bit i, while Qiskit prints the
    highest classical bit on the left. Reversing gives (b_0, b_1, ...).
    """
    compact = key.replace(" ", "")
    return tuple(int(bit) for bit in compact[::-1][:n])


def subset_from_bits(bits: tuple[int, ...]) -> set[int]:
    """Convert selector bits into I = {i : bit_i == 1}."""
    return {i for i, bit in enumerate(bits) if bit == 1}


def subset_total(xs: list[int], subset: set[int]) -> int:
    return sum(xs[i] for i in subset)


def verify_subset(xs: list[int], target: int, subset: set[int]) -> bool:
    return subset_total(xs, subset) == target


def exact_subset_sum(xs: list[int], target: int) -> set[int] | None:
    """
    Deterministic exhaustive checker.

    This is practical for the bootcamp requirement n <= 4. It is also useful as
    a verifier when the quantum sampling routine returns no candidate.
    """
    for bits in product([0, 1], repeat=len(xs)):
        subset = subset_from_bits(tuple(bits))
        if verify_subset(xs, target, subset):
            return subset
    return None


def build_grover_circuit(
    xs: list[int],
    target: int,
    grover_iterations: int,
    measure: bool = True,
) -> QuantumCircuit:
    """Build the weighted-adder Grover circuit for a fixed iteration count."""
    n = len(xs)
    oracle = subset_sum_oracle_weighted_adder(xs, target).to_gate()
    total_qubits = oracle.num_qubits
    diffusion = diffusion_operator(n, total_qubits).to_gate()

    qc = QuantumCircuit(total_qubits)
    qc.h(range(n))

    for _ in range(grover_iterations):
        qc.append(oracle, range(total_qubits))
        qc.append(diffusion, range(total_qubits))

    if measure:
        classical = ClassicalRegister(n, "c")
        qc.add_register(classical)
        for i in range(n):
            qc.measure(i, classical[i])

    return qc


def quantum_subset_sum(
    xs: list[int],
    target: int,
    shots: int = 2000,
    max_rounds: int | None = None,
    include_zero_iteration: bool = False,
    certify_small_no_solution: bool = True,
    verbose: bool = False,
) -> SubsetSumResult:
    """
    Try to solve subset sum with Grover search and a WeightedAdder oracle.

    Args:
        xs: positive integers [x_0, x_1, ..., x_{n-1}].
        target: target sum t.
        shots: samples per Grover iteration count.
        max_rounds: largest Grover iteration count to try. If None, use
            ceil((pi / 4) * sqrt(2^n)) + 1.
        include_zero_iteration: also test r = 0, which is just uniform random
            sampling before any Grover amplification.
        certify_small_no_solution: for n <= 20, do a classical exhaustive check
            before returning "no_solution_certified". For the bootcamp n <= 4
            requirement this makes the no-solution answer exact.
        verbose: print diagnostics.

    Returns:
        SubsetSumResult. If result.subset is not None, then
        sum(xs[i] for i in result.subset) == target.

    Notes:
        Without the optional exhaustive check, failure to observe a valid subset
        means "not found with the chosen shots/rounds", not a proof.
    """
    if not isinstance(target, int):
        raise TypeError("target must be an integer")
    if any(not isinstance(x, int) for x in xs):
        raise TypeError("all xs values must be integers")
    if any(x <= 0 for x in xs):
        raise ValueError("this implementation expects positive integers")
    if shots <= 0:
        raise ValueError("shots must be positive")

    if target < 0:
        return SubsetSumResult(None, None, None, "no_solution_certified", shots=0)
    xs = [int(x) for x in xs]
    if target == 0:
        return SubsetSumResult(set(), tuple(0 for _ in xs), 0, "found", 0, shots=0)
    if not xs:
        return SubsetSumResult(None, None, None, "no_solution_certified", shots=0)
    if target > sum(xs):
        return SubsetSumResult(None, None, None, "no_solution_certified", shots=0)

    n = len(xs)
    if max_rounds is None:
        max_rounds = ceil((pi / 4) * sqrt(2**n)) + 1
    if max_rounds < 0:
        raise ValueError("max_rounds must be nonnegative")

    simulator = AerSimulator()
    first_round = 0 if include_zero_iteration else 1
    if max_rounds < first_round:
        max_rounds = first_round

    if verbose:
        print("xs =", xs)
        print("target =", target)
        print("shots =", shots)
        print(f"trying Grover iterations {first_round}..", max_rounds)

    for grover_iterations in range(first_round, max_rounds + 1):
        qc = build_grover_circuit(xs, target, grover_iterations, measure=True)

        # Aer cannot directly run custom gates such as SubsetSumOracle.
        compiled_qc = transpile(qc, simulator)
        result = simulator.run(compiled_qc, shots=shots).result()
        counts = result.get_counts()
        ranked = sorted(counts.items(), key=lambda item: item[1], reverse=True)

        if verbose:
            print(f"r = {grover_iterations}, top outcomes = {ranked[:5]}")

        for key, _count in ranked:
            bits = decode_qiskit_key(key, n)
            subset = subset_from_bits(bits)
            total = subset_total(xs, subset)
            if total == target:
                return SubsetSumResult(
                    subset=subset,
                    bits=bits,
                    total=total,
                    status="found",
                    grover_iterations=grover_iterations,
                    shots=shots,
                )

    if certify_small_no_solution and n <= 20:
        exact = exact_subset_sum(xs, target)
        if exact is not None:
            bits = tuple(1 if i in exact else 0 for i in range(n))
            return SubsetSumResult(
                subset=exact,
                bits=bits,
                total=subset_total(xs, exact),
                status="found_by_classical_fallback",
                grover_iterations=None,
                shots=shots * (max_rounds - first_round + 1),
            )
        return SubsetSumResult(
            subset=None,
            bits=None,
            total=None,
            status="no_solution_certified",
            grover_iterations=None,
            shots=shots * (max_rounds - first_round + 1),
        )

    return SubsetSumResult(
        subset=None,
        bits=None,
        total=None,
        status="not_found_probabilistic",
        grover_iterations=None,
        shots=shots * (max_rounds - first_round + 1),
    )


if __name__ == "__main__":
    examples = [
        ([1, 2, 3], 3),
        ([2, 4, 7, 8], 9),
        ([2, 4, 6], 5),
    ]

    for values, target_sum in examples:
        answer = quantum_subset_sum(values, target_sum, verbose=True)
        print("\nanswer:", answer)
        print("-" * 60)
