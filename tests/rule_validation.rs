use quasar::*;
use std::collections::HashSet;

#[test]
fn rule_observation_is_not_input() {
    // 규칙: 관측은 입력이 아니라 조건
    let space = ArithmeticSpace::create_in_range(3, 0, 20);
    let tree = space.generate_tree(50);

    // 동일한 트리에서 여러 번 관측
    let result1 = observe(&tree, 3);
    let result2 = observe(&tree, 3);

    // 관측은 계산이 아니라 찾기 → 항상 동일한 결과
    assert_eq!(result1, result2, "관측은 결정론적이어야 함");
    assert!(!result1.is_empty(), "결과는 비어있지 않아야 함");

    println!("관측은 입력이 아니라 조건 (결과: {:?})", result1);
}

#[test]
fn rule_result_is_always_set() {
    // 규칙: 결과는 항상 집합 (단일 값이 아님)
    for start in 0..5 {
        let space = ArithmeticSpace::create_in_range(start, 0, 30);
        let tree = space.generate_tree(30);
        let result = observe(&tree, start);

        // 결과는 항상 집합 (최소 1개 이상)
        assert!(result.len() >= 1, "결과는 최소 1개 이상의 요소를 가져야 함");

        println!(
            " observe({}) → {:?} (크기: {})",
            start,
            result,
            result.len()
        );
    }
    println!("결과는 항상 집합");
}

#[test]
fn rule_single_collapse_multiple_projections() {
    // 규칙: 단일 collapse에서 다중 projection 가능
    let space = ArithmeticSpace::create_in_range(5, 0, 20);
    let tree = space.generate_tree(40);
    let collapsed = observe(&tree, 5);

    assert!(!collapsed.is_empty(), "collapse 결과는 비어있지 않아야 함");
    println!("collapse 결과: {:?} (크기: {})", collapsed, collapsed.len());

    let projections: Vec<(&str, Box<dyn Projection<i64>>)> = vec![
        ("수치적", Box::new(NextValues)),
        ("분류적", Box::new(OperationType)),
        ("크기적", Box::new(Magnitude)),
    ];

    for (name, proj) in projections {
        let result = proj.project(&collapsed);

        // 각 프로젝션이 유효한 결과를 반환하는지 확인
        assert!(!result.is_empty(), "프로젝션 결과는 비어있지 않아야 함");

        // 프로젝션별 특성 검증
        match name {
            "수치적" => {
                // NextValues: 각 값에 대해 "Next: 값+1"형식
                for s in &result {
                    assert!(
                        s.starts_with("Next: "),
                        "NextValues는 'Next: '로 시작해야 함"
                    );
                }
            }
            "분류적" => {
                // OperationType: "even"또는 "odd"만
                for s in &result {
                    assert!(
                        s == "even" || s == "odd",
                        "OperationType은 'even' 또는 'odd'여야 함"
                    );
                }
            }
            "크기적" => {
                // Magnitude: "large"또는 "small"만
                for s in &result {
                    assert!(
                        s == "large" || s == "small",
                        "Magnitude는 'large' 또는 'small'여야 함"
                    );
                }
            }
            _ => {}
        }

        println!(" {} 프로젝션: {:?} (크기: {})", name, result, result.len());
    }

    println!("단일 collapse에서 다중 projection 가능");
}

#[test]
fn rule_constraints_are_sets_not_sequences() {
    // 규칙: 제약조건은 순서가 없는 집합
    let constraints1 = HashSet::from([
        ArithmeticConstraint::InRange(0, 10),
        ArithmeticConstraint::Positive,
    ]);

    let constraints2 = HashSet::from([
        ArithmeticConstraint::Positive,
        ArithmeticConstraint::InRange(0, 10),
    ]);

    // 순서가 달라도 동일한 집합
    assert_eq!(constraints1, constraints2, "제약조건은 집합, 순서 없음");

    println!("제약조건은 순서가 없는 집합");
}

#[test]
fn rule_state_space_immutability() {
    // 규칙: 상태 공간은 불변
    let space1 = ArithmeticSpace::create(3);
    assert_eq!(space1.constraints.len(), 0, "원본 상태는 변경되지 않음");

    let space2 = space1.with_constraint(ArithmeticConstraint::InRange(0, 10));
    assert_eq!(space2.constraints.len(), 1, "새 인스턴스가 생성됨");

    println!("상태 공간은 불변 (새 인스턴스 생성)");
}
