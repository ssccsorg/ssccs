use ssccs_poc::*;

#[test]
fn test_constraint_set_composition() {
    // ConstraintSet 합성 테스트
    println!(" ConstraintSet 합성 테스트");

    let space1 = ArithmeticSpace::create_in_range(3, 0, 5);
    let space2 = ArithmeticSpace::create_in_range(3, 3, 10);

    let composite = compose_spaces(&space1, &space2);

    // 합성된 ConstraintSet 검증
    assert!(
        composite
            .allowed_coordinates()
            .contains(&SpaceCoordinates::new(vec![3]))
    );
    assert!(
        composite
            .allowed_coordinates()
            .contains(&SpaceCoordinates::new(vec![4]))
    );
    assert!(
        composite
            .allowed_coordinates()
            .contains(&SpaceCoordinates::new(vec![5]))
    );
    assert!(
        !composite
            .allowed_coordinates()
            .contains(&SpaceCoordinates::new(vec![0]))
    );
    assert!(
        !composite
            .allowed_coordinates()
            .contains(&SpaceCoordinates::new(vec![10]))
    );

    println!(" ConstraintSet 합성 검증 완료");
    println!("   Space1 허용: 0-5");
    println!("   Space2 허용: 3-10");
    println!("   합성 허용: 3-5");
}

#[test]
fn test_composite_space_functionality() {
    println!(" CompositeSpace 기능 테스트");

    // 기본 합성 테스트
    let space1 = ArithmeticSpace::create_in_range(3, 0, 5);
    let space2 = ArithmeticSpace::create_in_range(3, 3, 10);

    let composite = compose_spaces(&space1, &space2);

    // 통계 검증
    let stats = composite.statistics();
    assert!(stats.intersection_size > 0, "교집합이 있어야 함");
    assert!(stats.composition_ratio > 0.0, "합성 비율이 0보다 커야 함");
    assert!(stats.composition_ratio <= 1.0, "합성 비율이 1 이하여야 함");

    // 허용 좌표 검증
    assert!(composite.is_fully_allowed(&SpaceCoordinates::new(vec![3])));
    assert!(composite.is_fully_allowed(&SpaceCoordinates::new(vec![4])));
    assert!(composite.is_fully_allowed(&SpaceCoordinates::new(vec![5])));

    // 비허용 좌표 검증
    assert!(!composite.is_fully_allowed(&SpaceCoordinates::new(vec![0])));
    assert!(!composite.is_fully_allowed(&SpaceCoordinates::new(vec![10])));

    println!(" CompositeSpace 기본 기능 검증 완료");
    println!("   {}", composite.describe_composition());
}

#[test]
fn test_boundary_detection() {
    println!(" 경계면 탐지 테스트");

    // 서로 겹치지 않는 상태 공간
    let space1 = ArithmeticSpace::create_in_range(2, 0, 3);
    let space2 = ArithmeticSpace::create_in_range(8, 7, 10);

    let composite = compose_spaces(&space1, &space2);

    // 교집합이 없어야 함
    let stats = composite.statistics();
    assert_eq!(stats.intersection_size, 0, "교집합이 없어야 함");
    assert_eq!(stats.composition_ratio, 0.0, "합성 비율이 0이어야 함");

    // 허용 좌표도 없어야 함
    assert!(composite.allowed_coordinates().is_empty());

    println!(" 경계면(충돌) 상황 검증 완료");
    println!("   {}", composite.describe_composition());
}

#[test]
fn test_nested_constraints() {
    println!(" 중첩 제약조건 합성 테스트");

    // 여러 제약조건을 가진 상태 공간들
    let space1 = ArithmeticSpace::create(6)
        .with_constraint(ArithmeticConstraint::Even)
        .with_constraint(ArithmeticConstraint::InRange(0, 10));

    let space2 = ArithmeticSpace::create(6)
        .with_constraint(ArithmeticConstraint::MultipleOf(3))
        .with_constraint(ArithmeticConstraint::Positive);

    let composite = compose_spaces(&space1, &space2);

    // 두 제약조건 집합을 모두 만족하는 값들
    // 6: 짝수, 0-10 범위, 3의 배수, 양수
    assert!(composite.is_fully_allowed(&SpaceCoordinates::new(vec![6])));

    // 3: 3의 배수, 양수이지만 짝수가 아님 → 허용 안됨
    assert!(!composite.is_fully_allowed(&SpaceCoordinates::new(vec![3])));

    // 8: 짝수, 0-10 범위이지만 3의 배수가 아님 → 허용 안됨
    assert!(!composite.is_fully_allowed(&SpaceCoordinates::new(vec![8])));

    println!(" 중첩 제약조건 합성 검증 완료");
    println!("   Space1 제약: 짝수 & 0-10 범위");
    println!("   Space2 제약: 3의 배수 & 양수");
    println!("   공통 허용 값: 6");
}
