use std::collections::HashMap;
use std::io;
use std::io::{BufRead, stdin};
use Block::{HorizontalRule, Null};
use Inline::{Cite, LineBreak, Quoted, SmallCaps, SoftBreak, Space, Span, Strikeout, Subscript, Superscript};
use pandoc::definition::{Attr, AttrList, Block, Inline, Meta, MetaValue, Pandoc};
use pandoc::definition::Block::{BlockQuote, BulletList, CodeBlock, DefinitionList, Div, Header, LineBlock, OrderedList, Para, Plain, RawBlock, Table};
use pandoc::definition::Inline::{Code, Emph, Link, Math, Note, RawInline, Str, Strong, Underline};
use pandoc::definition::MetaValue::{MetaBlocks, MetaBool, MetaInlines, MetaList, MetaMap, MetaString};
use pandoc::walkable::{Blocks, Inlines, Walkable};

fn extract(meta: &Meta, key: &'static str) -> HashMap<String, String> {
    let mut environments = HashMap::<String, String>::new();
    if let Some(MetaList(envs)) = meta.get(key) {
        for value in envs.iter() {
            match value {
                MetaMap(dict) => {
                    for (key, value) in dict {
                        if let Some(value) = value.to_string_or_none() {
                            if !value.is_empty() {
                                environments.insert(key.clone(), value.clone());
                            }
                        }
                    }
                },
                _ => {
                    if let Some(value) = value.to_string_or_none() {
                        if !value.is_empty() {
                            environments.insert(value.clone(), value.clone());
                        }
                    }
                }
            }
        }
    } else if let Some(MetaMap(envs)) = meta.get(key) {
        for (key, value) in envs.iter() {
            if let Some(value) = value.to_string_or_none() {
                if !value.is_empty() {
                    environments.insert(key.clone(), value.clone());
                }
            }
        }
    }
    environments
}

fn extract_environemnts(meta: &Meta) -> HashMap<String, String> {
    extract(meta, "environments")
}

fn extract_commands(meta: &Meta) -> HashMap<String, String> {
    extract(meta, "commands")
}

fn get<'a>(attributes: &'a AttrList, selector: &'static str) -> Option<&'a String> {
    attributes.iter()
        .find(|(key, _)| key == &String::from(selector))
        .map(|(_, value)| value)
}

fn latex_block(latex: String) -> Block {
    RawBlock(String::from("latex"), latex)
}

fn transform_environments(block: Block, environments: &HashMap<String, String>) -> Blocks {
    match block {
        Div(Attr { classes, attributes, .. }, mut children) if environments.keys().any(|it| classes.contains(it)) => {
            let mut env_name = environments.iter().find(|it| classes.contains(it.0))
                .unwrap()
                .1
                .clone();
            if classes.contains(&String::from("unnumbered")) {
                env_name.push('*');
            }
            let mut begin = String::from("\\begin{");
            begin.push_str(&env_name);
            begin.push_str("}");
            if let Some(options) = get(&attributes, "options") {
                begin.push('[');
                begin.push_str(options);
                begin.push(']');
            }
            if let Some(arguments) = get(&attributes, "arguments") {
                begin.push('{');
                begin.push_str(arguments);
                begin.push('}');
            }

            let mut end = String::from("\\end{");
            end.push_str(&env_name);
            end.push_str("}\n");

            let mut blocks = Vec::with_capacity(2);
            blocks.push(latex_block(begin));
            blocks.append(&mut children);
            blocks.push(latex_block(end));
            blocks
        }
        _ => vec![block]
    }
}

fn latex_inline(latex: String) -> Inline {
    RawInline(String::from("latex"), latex)
}

fn transform_commands(inline: Inline, commands: &HashMap<String, String>) -> Inlines {
    match inline {
        Span(Attr { classes, attributes, .. }, mut children) if commands.keys().any(|it| classes.contains(it)) => {
            let mut env_name = commands.iter().find(|it| classes.contains(it.0))
                .unwrap()
                .1
                .clone();
            if classes.contains(&String::from("unnumbered")) {
                env_name.push('*');
            }
            let mut begin = String::from("\\");
            begin.push_str(&env_name);
            if let Some(options) = get(&attributes, "options") {
                begin.push('[');
                begin.push_str(options);
                begin.push(']');
            }
            if let Some(arguments) = get(&attributes, "arguments") {
                begin.push('{');
                begin.push_str(arguments);
                begin.push('}');
            }
            begin.push_str("{");

            let end = String::from("}");

            let mut inlines = Vec::with_capacity(children.len() + 2);
            inlines.push(latex_inline(begin));
            inlines.append(&mut children);
            inlines.push(latex_inline(end));
            inlines
        }
        _ => vec![inline]
    }
}

fn main() -> io::Result<()> {
    let args = std::env::args().collect::<Vec<_>>();
    let format = &args[0];
    let mut pandoc_json = String::new();
    for line in stdin().lock().lines() {
        if let Ok(line) = line {
            pandoc_json += line.as_str();
        }
    }
    let mut pandoc: Pandoc = serde_json::from_str(&pandoc_json)?;
    if format == &String::from("latex") {
        let environments = extract_environemnts(&pandoc.meta);
        eprintln!("{:?}", environments);
        let mut transform_environments = |b: Block| { transform_environments(b, &environments) };
        let commands = extract_commands(&pandoc.meta);
        eprintln!("{:?}", commands);
        let mut transform_commands = |i: Inline| { transform_commands(i, &commands) };
        pandoc = pandoc
            .walk(&mut transform_environments)
            .walk(&mut transform_commands);
    }
    println!("{}", serde_json::to_string(&pandoc)?);
    Ok(())
}

trait ToStringOrNone {
    fn to_string_or_none(&self) -> Option<String>;
}

impl ToStringOrNone for MetaValue {
    fn to_string_or_none(&self) -> Option<String> {
        match self {
            MetaMap(map) => map.values().cloned().collect::<Vec<_>>().to_string_or_none(),
            MetaList(children) => children.to_string_or_none(),
            MetaBool(boolean) => Some(boolean.to_string()),
            MetaString(text) => Some(text.clone()),
            MetaInlines(children) => children.to_string_or_none(),
            MetaBlocks(children) => children.to_string_or_none(),
        }
    }
}

impl ToStringOrNone for Inline {
    fn to_string_or_none(&self) -> Option<String> {
        match self {
            Str(text) => Some(text.clone()),
            Emph(children) => children.to_string_or_none(),
            Underline(children) => children.to_string_or_none(),
            Strong(children) => children.to_string_or_none(),
            Strikeout(children) => children.to_string_or_none(),
            Superscript(children) => children.to_string_or_none(),
            Subscript(children) => children.to_string_or_none(),
            SmallCaps(children) => children.to_string_or_none(),
            Quoted(_, children) => children.to_string_or_none(),
            Cite(_, _) => None,
            Code(_, text) => Some(text.clone()),
            Space => Some(String::from(' ')),
            SoftBreak => Some(String::from(' ')),
            LineBreak => Some(String::from('\n')),
            Math(_, text) => Some(text.clone()),
            RawInline(_, text) => Some(text.clone()),
            Link(_, children, _) => children.to_string_or_none(),
            Note(children) => children.to_string_or_none(),
            Span(_, children) => children.to_string_or_none(),
            _ => None
        }
    }
}

impl<T: ToStringOrNone> ToStringOrNone for Vec<T> {
    fn to_string_or_none(&self) -> Option<String> {
        let content = self.iter()
            .filter_map(|it| it.to_string_or_none())
            .collect::<Vec<_>>();
        if content.is_empty() {
            None
        } else {
            Some(content.join(""))
        }
    }
}

impl ToStringOrNone for Block {
    fn to_string_or_none(&self) -> Option<String> {
        match self {
            Plain(children) => children.to_string_or_none(),
            Para(children) => children.to_string_or_none(),
            LineBlock(children) => children.to_string_or_none(),
            CodeBlock(_, text) => Some(text.clone()),
            RawBlock(_, text) => Some(text.clone()),
            BlockQuote(children) => children.to_string_or_none(),
            OrderedList(_, _) => None,
            BulletList(_) => None,
            DefinitionList(_) => None,
            Header(_, _, children) => children.to_string_or_none(),
            HorizontalRule => None,
            Table(_, _, _, _, _, _) => None,
            Div(_, children) => children.to_string_or_none(),
            Null => None,
        }
    }
}