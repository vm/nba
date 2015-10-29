extern crate chrono;
extern crate hyper;
extern crate regex;
extern crate select;

use std::collections::HashSet;

use chrono::{DateTime, UTC};
use hyper::Client;
use hyper::header::Connection;
use regex::Regex;
use select::document::Document;
use select::predicate::{Attr, Name};
use select::selection::Selection;

static GAME_RESULT_RE: Regex = Regex::new(r".*?\((.*?)\)").unwrap();

enum Stat {
    Num(usize),
    MaybeNum(Option<usize>),
    Team(String),
    Text(String),
    Margin(Option<isize>),
    Date(DateTime<UTC>)
}

type Gamelog = Vec<(String, Stat)>;

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
            .get(self.url)
            .connection(Connection::close())
            .send()
            .unwrap();
        res.read_to_string(self.body).unwrap();
    }

    fn find_gamelogs(page: &Document, table_name: &str) -> Vec<Gamelog> {
        GamelogTable::New(page.find(Attr("id", table_name))).gamelogs()
    }

    pub fn gamelogs(&mut self) -> Option<Vec<Gamelog>>{
        let page = Document::from_str(self.body);
        let mut gamelogs = Vec::new();
        let reg_gamelogs = self.find_gamelogs(&page, "pgl_basic");
        let playoff_gamelogs = self.find_gamelogs(&page, "pgl_basic_playoffs");
        if let Some(reg) = reg_gamelogs { gamelogs.push_all(reg); }
        if let Some(playoff) = playoff_gamelogs { gamelogs.push_all(playoff); }
        if gamelogs.is_empty() { None } else { Some(gamelogs) }
    }
}

struct GamelogTable(Selection);

impl GamelogTable {
    fn new(table: Selection) -> GamelogTable { GamelogTable(table) }

    pub fn gamelogs(&self) -> Option<Vec<Gamelog>> {
        let names = vec![
            "rk", "num", "date", "team", "date", "is_home", "opp", "result",
            "min", "fg", "fga", "tp", "tpa", "ft", "fta", "orb", "drb", "ast",
            "stl", "blk", "tov", "pf", "pts", "margin"
        ];
        self.0.map(|table| table
                   .find(Name("tr"))
                   .iter()
                   .skip(1)
                   .map(Self::parse_row)
                   .zip(names
                        .iter()
                        .map(str::to_owned))
                   .collect())
    }

    fn parse_row(row: Selection) -> Gamelog {
        row
            .find(Name("td"))
            .iter()
            .enumerate()
            .filter(|(i, _)| ![3, 12, 15, 18, 21, 28].contains(i))
            .map(Self::parse_col)
            .collect()
    }

    fn parse_col(index: usize, col: Selection) -> Stat {
        let text_option = col.map(Selection::text);
        match &index {
            0 => Stat::Num(text_option.unwrap() as usize),
            1 => Stat::Num(Self::remove_empty(text_option)),
            2 => {
                let date = text_option.unwrap().split("-");
                let (y, m, d) = (date[0], date[1], date[2]);
                Stat::Date(UTC.ymd(y, m, d))
            },
            4 | 6 => Stat::Team(text_option),
            5 => Stat::Bool(text_option.map(|x| {
                match x {
                    "" => true,
                    "@" => false,
                    _ => unreachable!(),
                }
            })),
            7 => Stat::Margin(text_option.map(|t| GAME_RESULT_RE
                                              .find(t)
                                              .first())
                              as usize),
            8 => Stat::Bool(text_option.map(|x| x != "1")),
            9 => Stat::MaybeNum(Self::remove_empty(text_option)
                                .map(|x| x
                                     .split(":")
                                     .first())),
            10...12 | 13...15 | 16...18 | 19...21 | 22...28 | 29 =>
                Stat::MaybeNum(Self::remove_empty(text_option)),
            _ => unreachable!(),
        }
    }

    fn remove_empty(text_option: Option<String>) -> Option<usize> {
        text_option
            .and_then(|text| {
                if let text = "" { None } else { Some(text as usize) }
            })
    }
}

fn main() {
    println!("it compiles!")
}
