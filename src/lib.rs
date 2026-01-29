extern crate proc_macro;
use proc_macro::TokenStream;
use quote::quote;
use syn::parse_macro_input;
use syn::Ident;

#[proc_macro]
pub fn state_space(input: TokenStream) -> TokenStream {
    let name = parse_macro_input!(input as Ident);
    
    let expanded = quote! {
        // 상태 공간 구조체 생성
        #[derive(Clone, Debug)]
        pub struct #name {
            value: i64,
            children: Vec<#name>,
            computed: bool,
        }
        
        impl #name {
            pub fn new(value: i64) -> Self {
                // 간단한 제약 조건: 0 <= x <= 10
                if value < 0 || value > 10 {
                    panic!("Constraint violated: x must be between 0 and 10, got {}", value);
                }
                
                Self {
                    value,
                    children: Vec::new(),
                    computed: false,
                }
            }
            
            // 가능한 모든 전이 계산 (최대 깊이 제한 추가)
            pub fn compute_trajectories(&mut self) {
                self.compute_trajectories_with_depth(0, 5); // 최대 깊이 5로 제한
            }
            
            fn compute_trajectories_with_depth(&mut self, depth: usize, max_depth: usize) {
                if self.computed || depth >= max_depth {
                    return;
                }
                
                let x = self.value;
                
                // 두 가지 가능한 전이
                let candidates = vec![x + 1, x * 2];
                
                for candidate in candidates {
                    if candidate >= 0 && candidate <= 10 {
                        let mut child = #name::new(candidate);
                        child.compute_trajectories_with_depth(depth + 1, max_depth);
                        self.children.push(child);
                    }
                }
                
                self.computed = true;
            }
            
            // 관찰: 특정 값에서 collapse (비재귀 버전)
            pub fn observe(&self, target: i64) -> Option<Vec<i64>> {
                // 스택을 사용한 비재귀 탐색
                let mut stack = vec![self];
                let mut visited = std::collections::HashSet::new();
                
                while let Some(current) = stack.pop() {
                    if visited.contains(&current.value) {
                        continue;
                    }
                    visited.insert(current.value);
                    
                    if current.value == target {
                        // 이 상태에서 가능한 다음 값들
                        return Some(current.children.iter().map(|c| c.value).collect());
                    }
                    
                    // 자식들 스택에 추가
                    for child in &current.children {
                        stack.push(child);
                    }
                }
                
                None
            }
            
            // 전체 trajectory 출력 (깊이 제한)
            pub fn print_trajectories(&self, depth: usize) {
                if depth > 5 { // 출력 깊이 제한
                    println!("{}... (depth limit)", "  ".repeat(depth));
                    return;
                }
                
                let indent = "  ".repeat(depth);
                println!("{}{}", indent, self.value);
                for child in &self.children {
                    child.print_trajectories(depth + 1);
                }
            }
        }
    };
    
    TokenStream::from(expanded)
}

#[proc_macro]
pub fn projection(input: TokenStream) -> TokenStream {
    let name = parse_macro_input!(input as Ident);
    
    let expanded = quote! {
        #[derive(Debug)]
        pub struct #name;
        
        impl #name {
            pub fn apply(&self, values: &[i64]) -> Vec<String> {
                values.iter().map(|&x| {
                    // 간단한 프로젝션 로직
                    if stringify!(#name).contains("Next") {
                        format!("Next: {}", x + 1)
                    } else if stringify!(#name).contains("Growth") {
                        if x % 2 == 0 {
                            "even".to_string()
                        } else {
                            "odd".to_string()
                        }
                    } else if stringify!(#name).contains("Magnitude") {
                        if x > 5 {
                            "large".to_string()
                        } else {
                            "small".to_string()
                        }
                    } else {
                        format!("Value: {}", x)
                    }
                }).collect()
            }
        }
    };
    
    TokenStream::from(expanded)
}