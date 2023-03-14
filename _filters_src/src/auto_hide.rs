use std::io;
use std::io::{BufRead, stdin};
use pandoc::definition::{Attr, Block, Meta, MetaValue, Pandoc};
use pandoc::walkable::Walkable;

fn is_code_cell(attr: &Attr) -> bool {
    attr.classes.contains(&String::from("cell")) &&
        attr.classes.contains(&String::from("code"))
}

fn is_kernel_code_block(attr: &Attr, kernel_language: &String) -> bool {
    attr.classes.contains(kernel_language)
}

fn is_visible(attr: &Attr) -> bool {
    attr.classes.contains(&String::from("visible")) ||
        attr.attributes.iter()
            .find(|(k, v)| k == &String::from("tags") || v.contains("visible"))
            .is_some()
}

fn extract_kernel_language(meta: &Meta) -> Option<String> {
    if let Some(MetaValue::MetaMap(jupyter)) = meta.get(&String::from("jupyter")) {
        if let Some(MetaValue::MetaMap(kernelspec)) = jupyter.get(&String::from("kernelspec")) {
            if let Some(MetaValue::MetaString(language)) = kernelspec.get(&String::from("language")) {
                return Some(language.clone());
            }
        }
    }
    None
}

fn auto_hide(block: Block, kernel_language: &Option<String>) -> Block {
    if let Some(kernel_language) = kernel_language {
        match block {
            Block::Div(attr, blocks) if is_code_cell(&attr) => {
                let parent_attr = attr.clone();
                Block::Div(
                    attr,
                    blocks.iter()
                        .flat_map(|it| {
                            match it {
                                Block::CodeBlock(attr, _) if is_kernel_code_block(attr, kernel_language) && !is_visible(&parent_attr) => None,
                                _ => Some(it)
                            }
                        })
                        .cloned()
                        .collect(),
                )
            }
            _ => block
        }
    } else {
        block
    }
}

fn main() -> io::Result<()> {
    to_json_filter(&mut auto_hide, &mut extract_kernel_language)
}

pub fn to_json_filter<F, I, O, S, M>(f: &mut F, select: &mut S) -> io::Result<()>
    where
        Pandoc: Walkable<I, O>,
        F: FnMut(I, &M) -> O,
        S: FnMut(&Meta) -> M,
{
    let mut pandoc_json = String::new();
    for line in stdin().lock().lines() {
        if let Ok(line) = line {
            pandoc_json += line.as_str();
        }
    }
    let pandoc: Pandoc = serde_json::from_str(&pandoc_json)?;
    let meta = select(&pandoc.meta);
    let mut inner_f = |i: I| { f(i, &meta) };
    println!("{}", serde_json::to_string(&pandoc.walk(&mut inner_f))?);
    Ok(())
}
