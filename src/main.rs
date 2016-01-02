#![feature(vec_push_all)]

extern crate chrono;
extern crate hyper;
extern crate regex;
extern crate select;

use std::collections::HashSet;
use std::io::Read;

use chrono::{DateTime, UTC};
use hyper::Client;
use hyper::header::Connection;
use regex::Regex;
use select::document::Document;
use select::node::Node;
use select::predicate::{Attr, Name};
use select::selection::Selection;

#[derive(Clone)]
enum Stat {
    Num(usize),
    MaybeNum(Option<usize>),
    Team(String),
    Text(String),
    Bool(Option<bool>),
    Margin(Option<isize>),
    Date(DateTime<UTC>),
}

type Gamelog = bool;

pub struct SeasonPage {
    url: String,
    body: String,
}

impl SeasonPage {
    pub fn new(url: String) -> SeasonPage {
        SeasonPage {
            url: url,
            body: String::new(),
        }
    }

    pub fn download(&mut self) {
        let mut client = Client::new();
        let mut res = client
            .get(&self.url)
            .header(Connection::close())
            .send()
            .unwrap();
        res.read_to_string(&mut self.body).unwrap();
    }

    fn find_gamelogs(page: &Document, table_name: &str) -> Option<bool> {
        GamelogTable::new(page
                          .find(Attr("id", table_name))
                          .first())
            .gamelogs()
    }

    pub fn gamelogs(&self) -> Option<Vec<bool>>{
        let page = Document::from_str(&self.body);
        let mut gamelogs = Vec::new();
        let reg_gamelogs = Self::find_gamelogs(&page, "pgl_basic");
        let playoff_gamelogs = Self::find_gamelogs(&page, "pgl_basic_playoffs");
        if let Some(reg) = reg_gamelogs {
            println!("there were some");
            // gamelogs.append(&mut reg);
        }
        if let Some(playoff) = playoff_gamelogs {
            println!("meow");
            //gamelogs.append(&mut playoff);
        }
        if gamelogs.is_empty() { None } else { Some(gamelogs) }
    }
}

struct GamelogTable<'a> {
    table: Option<Node<'a>>,
}

impl<'a> GamelogTable<'a> {
    fn new(table: Option<Node<'a>>) -> GamelogTable {
        GamelogTable {
            table: table
        }
    }

    pub fn gamelogs(&self) -> Option<bool> {
        let names = vec![
            "rk", "num", "date", "team", "date", "is_home", "opp", "result",
            "min", "fg", "fga", "tp", "tpa", "ft", "fta", "orb", "drb", "ast",
            "stl", "blk", "tov", "pf", "pts", "margin"
        ];
        if let Some(t) = self.table {
            println!("{}", t.text());
        } else {
            println!("nope");
        }
        self.table.map(|t| true)
    }

    fn parse_row(row: Option<Node<'a>>) -> Option<bool> {
        row.map(|r| true)
        // row.map(|r| r
        //         .find(Name("td"))
        //         .iter()
        //         .enumerate()
        //         .filter(|(i, _)| ![3, 12, 15, 18, 21, 28].contains(i))
        //         .map(Self::parse_col)
        //         .collect())
    }

//    fn parse_col(index: usize, col: Option<Node<'a>>) -> Stat {
//        let text_option = col.map(|x| x.text());
//        match index {
//            0 => Stat::Num(text_option.unwrap() as usize),
//            1 => Stat::Num(Self::remove_empty(text_option)),
//            2 => {
//                let date = text_option.unwrap().split("-");
//                let (y, m, d) = (date[0], date[1], date[2]);
//                Stat::Date(UTC.ymd(y, m, d))
//            },
//            4 | 6 => Stat::Team(text_option),
//            5 => Stat::Bool(text_option.map(|x| {
//                match x {
//                    "" => true,
//                    "@" => false,
//                    _ => unreachable!(),
//                }
//            })),
//            7 => Stat::Margin(text_option.map(|t| GAME_RESULT_RE
//                                              .find(t)
//                                              .first())
//                              as usize),
//            8 => Stat::Bool(text_option.map(|x| x != "1")),
//            9 => Stat::MaybeNum(Self::remove_empty(text_option)
//                                .map(|x| x
//                                     .split(":")
//                                     .first())),
//            10...12 | 13...15 | 16...18 | 19...21 | 22...28 | 29 =>
//                Stat::MaybeNum(Self::remove_empty(text_option)),
//            _ => unreachable!(),
//        }
//    }
//
//    fn remove_empty(text_option: Option<String>) -> Option<usize> {
//        text_option.and_then(|text| {
//            if let text = "" { None } else { Some(text as usize) }
//        })
//    }
}

fn main() {
    SeasonPage::new("basketball-reference.com/players/c/curryst01/gamelog/2015/".to_owned())
        .gamelogs();
}
