use std::io;
use pandoc::definition::{Attr, Block};
use pandoc::to_json_filter;
use pandoc::walkable::Blocks;

fn is_ipynb_cell(attr: &Attr) -> bool {
    attr.classes.contains(&String::from("cell"))
}

fn flatten_ipynb(block: Block) -> Blocks {
    match block {
        Block::Div(attr, blocks) if is_ipynb_cell(&attr) => blocks,
        _ => vec![block]
    }
}

fn main() -> io::Result<()> {
    to_json_filter(&mut flatten_ipynb)
}