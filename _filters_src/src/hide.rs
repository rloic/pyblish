use std::io;
use pandoc::definition::{Attr, Block};
use pandoc::to_json_filter;
use pandoc::walkable::Blocks;

fn is_hidden(attr: &Attr) -> bool {
    attr.classes.contains(&String::from("hidden")) ||
        attr.attributes.iter().find(|(k, v)| k == &String::from("tags") && v.contains("hidden")).is_some()
}

fn hide(block: Block) -> Blocks {
    match block {
        Block::Div(attr, _) if is_hidden(&attr) => vec![],
        _ => vec![block]
    }
}

fn main() -> io::Result<()> {
    to_json_filter(&mut hide)
}
