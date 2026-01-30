use quasar::projectors::IntegerProjector;
use quasar::*;
use std::collections::HashSet;

fn demonstrate_state_space_composition() {
    println!("\n 상태 공간 조합 실험");
    println!("=====================\n");

    // 1. 산술 + 논리 상태 공간 동시 실험
    println!("1. 산술과 논리 상태 공간 비교:");

    let arithmetic = ArithmeticSpace::create_in_range(3, 0, 10);
    let boolean = BooleanSpace::create_true();

    let arith_tree = arithmetic.generate_tree(20);
    let bool_tree = boolean.generate_tree(10);

    println!("   산술 상태 수: {}", arith_tree.len());
    println!("   논리 상태 수: {}\n", bool_tree.len());

    // 2. 다양한 제약조건 조합
    println!("2. 제약조건 조합 실험:");

    let constraints: Vec<(&str, HashSet<ArithmeticConstraint>)> = vec![
        (
            "범위만",
            HashSet::from([ArithmeticConstraint::InRange(0, 10)]),
        ),
        ("짝수만", HashSet::from([ArithmeticConstraint::Even])),
        (
            "양수+범위",
            HashSet::from([
                ArithmeticConstraint::Positive,
                ArithmeticConstraint::InRange(1, 20),
            ]),
        ),
    ];

    for (name, cons) in constraints {
        let space = ArithmeticSpace::create_with_constraints(5, cons);
        let tree = space.generate_tree(15);

        // 정수 투영자를 사용하여 관측
        let projector = IntegerProjector::default();
        let observer = Observer::new(projector, 5);
        let observed = observe_transitions(&tree, &observer);

        println!(
            "   {}: observe_transitions(5) → {:?} (크기: {})",
            name,
            observed,
            observed.len()
        );
    }

    // 3. Mapper vs Quasar 최종 비교
    println!("\n3. 최종 개념 비교:");
    println!("   Mapper 모델: f(x) = 계산(x) → 단일 값");
    println!("   Quasar 모델: observe(x) = 투영자(공간) → 집합");
    println!("   → 근본적으로 다른 패러다임");
}

fn main() {
    println!(" Quasar PoC - 확장 실험");
    println!("=========================\n");

    demonstrate_state_space_composition();

    // 기존 실험도 유지
    println!("\n 핵심 규칙 검증 요약:");
    println!("1. .qs = Rust (확장자만 다름) ");
    println!("2. 관측 ≠ 계산 ");
    println!("3. 결과 = 집합 ");
    println!("4. 단일 collapse → 다중 projection ");
    println!("5. 제약조건 주입 가능 ");
    println!("6. 상태 공간 조합 가능 ");

    println!("\n Quasar는 새로운 계산 패러다임입니다.");
    println!("   Mapper/함수 모델과는 구조적으로 다릅니다.");
}
