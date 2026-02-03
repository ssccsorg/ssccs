use ssccs_poc::arithmetic::ArithmeticSpace;
use ssccs_poc::basic::BasicSpace;
use ssccs_poc::fields::FieldBuilder;
use ssccs_poc::spaces::*;
use ssccs_poc::*;

fn main() {
    println!(" Quasar: State-Space Computing (StateField 버전)");
    println!("==================================================\n");

    // 1. 기본 구조 실험
    println!(" 1. 기본 구조 실험:");
    let coords = SpaceCoordinates::new(vec![1, 2, 3]);
    println!("   순수 좌표: {:?}", coords.raw);
    println!("   좌표는 의미 없음: 단지 숫자 배열");
    println!();

    // 2. 상태 공간 생성
    println!(" 2. 상태 공간 생성:");
    let basic_space = basic::BasicSpace::new(coords.clone());
    println!("   BasicSpace 좌표: {:?}", basic_space.coordinates().raw);

    // StateField로 감싸기
    let basic_field: StateField<BasicSpace, i64, i64> =
        fields::FieldBuilder::<BasicSpace, i64, i64>::new(basic_space.clone())
            .add_constraint(RangeConstraint::new(0, 0, 10))
            .add_constraint(RangeConstraint::new(1, 0, 5))
            .build();

    println!(
        "   StateField 제약조건: {}",
        basic_field.constraints.describe()
    );
    println!("   허용 여부: {}", basic_field.is_allowed());
    println!();

    // 3. 제약조건 추가
    println!(" 3. 제약조건 추가:");
    let constrained_field: StateField<BasicSpace, i64, i64> =
        FieldBuilder::new(basic::BasicSpace::new(coords.clone()))
            .add_constraint(RangeConstraint::new(0, 0, 10))
            .add_constraint(RangeConstraint::new(1, 0, 5))
            .build();

    println!("   제약조건: {}", constrained_field.constraints.describe());
    println!(
        "   좌표 [1,2,3] 허용 여부: {}",
        constrained_field.is_allowed()
    );
    println!("   제약조건은 공간의 구조적 제한");
    println!();

    // 4. 투영 실험
    println!(" 4. 투영 실험:");
    let projector = IntegerProjector::new(0);
    let projection = projector.project(&coords);
    println!("   투영자: 첫 번째 축 값 추출");
    println!("   투영 결과: {:?}", projection);
    println!("   동일 좌표 → 다른 투영자 → 다른 의미");
    println!();

    // 5. 산술 공간 실험
    println!(" 5. 산술 공간 실험:");
    let arithmetic_space = arithmetic::ArithmeticSpace::new(5);
    println!(
        "   산술 공간 좌표: {:?}",
        arithmetic_space.coordinates().raw
    );
    println!("   산술 인접성: +1, -1, ×2, ×² 등");

    let arithmetic_field: StateField<ArithmeticSpace, i64, i64> =
        FieldBuilder::new(arithmetic_space.clone())
            .add_constraint(RangeConstraint::new(0, 0, 50))
            .build();

    let direct = observe_field(&arithmetic_field, &projector);
    println!("   직접 관측: {:?}", direct);

    // 인접 관측 (가능한 전이들)
    let possible_transitions = arithmetic_field.possible_transitions();
    println!("   가능한 전이들: {}개", possible_transitions.len());
    println!(
        "   전이 예시: {:?}",
        possible_transitions
            .iter()
            .take(3)
            .map(|s| s.coordinates().raw[0])
            .collect::<Vec<_>>()
    );
    println!();

    // 6. 트리 탐색
    println!(" 6. 트리 탐색:");
    let tree_results = observe_tree(&arithmetic_field, &projector, 2);
    println!("   깊이 2 탐색 결과: {:?}", tree_results);
    println!("   탐색된 값들: {}개", tree_results.len());
    println!();

    // 7. 관측자 패턴
    println!(" 7. 관측자 패턴:");
    let observer = ValueObserver::new(5, "값이 5인지 확인");

    // 현재 값 관측
    let current_value = projector.project(&arithmetic_field.space.coordinates());
    if let Some(value) = current_value {
        println!("   현재 값: {}", value);
        println!("   관측 결과: {}", observer.observe(&value));
        println!("   관측 설명: {}", observer.describe());
    }

    // 전이된 값 관측
    if let Some(first_transition) = possible_transitions.first() {
        let transition_value = projector.project(&first_transition.coordinates());
        if let Some(value) = transition_value {
            println!("   전이 값: {}", value);
            println!("   관측 결과: {}", observer.observe(&value));
        }
    }
    println!("   관측 = 투영 + 기대값 비교");
    println!();

    // 8. 합성 실험
    println!(" 8. 공간 합성:");
    let space1_field: StateField<BasicSpace, i64, i64> =
        FieldBuilder::new(basic::BasicSpace::new(SpaceCoordinates::new(vec![1, 2])))
            .add_constraint(RangeConstraint::new(0, 0, 5))
            .build();

    let space2_field: StateField<BasicSpace, i64, i64> =
        FieldBuilder::new(basic::BasicSpace::new(SpaceCoordinates::new(vec![1, 2])))
            .add_constraint(RangeConstraint::new(0, 0, 3))
            .build();

    let composition = compose_fields(&space1_field, &space2_field);
    println!("   합성 결과: {:?}", composition);
    println!("   합성 = 공간 간 관계 분석");
    println!();

    // 9. 짝수 제약조건 테스트
    println!(" 9. 짝수 제약조건 테스트:");
    let even_space = arithmetic::ArithmeticSpace::new(6);
    let even_field: StateField<ArithmeticSpace, i64, i64> = FieldBuilder::new(even_space)
        .add_constraint(EvenConstraint::new(0))
        .add_constraint(RangeConstraint::new(0, 0, 20))
        .build();

    println!("   좌표: {:?}", even_field.space.coordinates().raw);
    println!("   제약조건: {}", even_field.constraints.describe());
    println!("   허용 여부: {}", even_field.is_allowed());

    let even_transitions = even_field.possible_transitions();
    println!(
        "   짝수 제약하의 가능한 전이들: {}개",
        even_transitions.len()
    );
    println!(
        "   전이 값들: {:?}",
        even_transitions
            .iter()
            .map(|s| s.coordinates().raw[0])
            .collect::<Vec<_>>()
    );
    println!();

    // 철학적 요약
    println!(" 철학적 계층 구조:");
    println!("• 좌표는 구조: SpaceCoordinates([x, y, z])");
    println!("• StateSpace = 구조 + 기본 인접성");
    println!("• StateField = StateSpace + 동적 Field (제약, 전이, 관측)");
    println!("• 제약은 허용 영역: Constraint.allows(coords)");
    println!("• 투영은 의미 창발: Projector.project(coords)");
    println!("• 관측은 의미 검증: Observer.observe(value)");
    println!();

    println!(" Quasar: 상태는 불변, 조건은 가변, 의미는 창발!");
}
