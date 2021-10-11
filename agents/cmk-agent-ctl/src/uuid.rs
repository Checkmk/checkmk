use uuid::Uuid;

pub fn make() -> String {
    return Uuid::new_v4().to_string();
}
