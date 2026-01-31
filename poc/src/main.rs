use ssccs_poc::projectors::IntegerProjector;
use ssccs_poc::*;
use std::collections::HashSet;

fn demonstrate_state_space_composition() {
    println!("\n 상태 공간 조합 실험");
    println!("=====================\n");

    // 1. 산술 상태 공간 테스트
    println!("1. 산술 상태 공간 테스트:");

    let arithmetic = ArithmeticSpace::create_in_range(3, 0, 10);
    println!("   초기 상태: {:?}", arithmetic.coordinates());
    println!("   제약조건: {:?}", arithmetic.constraints);

    let arith_tree = arithmetic.generate_tree(10);
    println!("   생성된 상태 수: {}", arith_tree.len());

    // 2. ConstraintSet 합성 실험
    println!("\n2. ConstraintSet 합성 실험:");

    // 다양한 범위의 상태 공간들
    let spaces = vec![
        ("좁은 범위", ArithmeticSpace::create_in_range(5, 0, 5)),
        ("중간 범위", ArithmeticSpace::create_in_range(5, 3, 7)),
        ("넓은 범위", ArithmeticSpace::create_in_range(5, 0, 10)),
    ];

    for i in 0..spaces.len() {
        for j in i + 1..spaces.len() {
            let (name1, space1) = &spaces[i];
            let (name2, space2) = &spaces[j];

            let composite = compose_spaces(space1, space2);

            println!("\n   {} ∩ {}:", name1, name2);
            println!("   {}", composite.describe_composition());

            // 허용 좌표 예시 출력
            let allowed = composite.allowed_coordinates();
            let sample: Vec<String> = allowed
                .iter()
                .take(3)
                .map(|coord| format!("{:?}", coord.raw))
                .collect();

            println!("   허용 좌표 예시: {:?}", sample);
            if allowed.len() > 3 {
                println!("   허용 (총 {}개)", allowed.len());
            }
        }
    }

    // 3. 투영 및 관측 테스트
    println!("\n3. 투영 및 관측 테스트:");

    let space = ArithmeticSpace::create_in_range(5, 0, 15);
    let tree = space.generate_tree(20);

    let projector = IntegerProjector::default();
    let observer = Observer::new(projector, 5);
    let observed = observe_transitions(&tree, &observer);

    println!("   트리 크기: {}", tree.len());
    println!("   관측 결과: {:?}", observed);

    // 4. 다양한 제약조건 조합
    println!("\n4. 다양한 제약조건 조합:");

    let constraint_combinations = vec![
        (
            "범위+양수",
            HashSet::from([
                ArithmeticConstraint::InRange(0, 10),
                ArithmeticConstraint::Positive,
            ]),
        ),
        (
            "짝수+범위",
            HashSet::from([
                ArithmeticConstraint::Even,
                ArithmeticConstraint::InRange(2, 8),
            ]),
        ),
        (
            "3의배수+양수",
            HashSet::from([
                ArithmeticConstraint::MultipleOf(3),
                ArithmeticConstraint::Positive,
            ]),
        ),
    ];

    for (name, constraints) in constraint_combinations {
        let space = ArithmeticSpace::create_with_constraints(6, constraints);
        let tree = space.generate_tree(15);

        println!("\n   {}:", name);
        println!("   제약조건: {:?}", space.constraints);
        println!("   허용 좌표 수: {}", space.constraint_set().allowed.len());
        println!("   생성된 상태 수: {}", tree.len());
    }
}

fn main() {
    println!(" SSCCS PoC - ConstraintSet 합성 및 분석");
    println!("==========================================\n");

    demonstrate_state_space_composition();

    println!("\n 실험 결과 요약:");
    println!("1. ConstraintSet 합성으로 상태 공간 교집합 계산 가능");
    println!("2. 합성 통계(교집합 크기, 비율)로 호환성 분석 가능");
    println!("3. 경계면 좌표 탐색으로 충돌 지점 식별 가능");
    println!("4. 다양한 제약조건 조합 실험 완료");

    println!("\n SSCCS: 제약조건 집합 기반 상태 공간 합성 시스템");
}
