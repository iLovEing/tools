import argparse
import time
import pandas as pd
import numpy as np
import os
import json


time_now = time.strftime('%Y-%m-%d', time.localtime())
csv_file = 'record/item.csv'
json_file = 'summary/summary.json'
class_dict = {
    '0': 'music',
    '1': 'PS',
    '2': 'dota2',
    '3': 'PC',
    '4': 'others'
}
pf_dict = {
    '0': 'TB',
    '1': 'JD',
    '2': 'XY',
    '3': "PDD",
    '4': 'others',
}


funds_one_year = 12000
# 2020: 7000, 2025: 8000
pc_founds = 7000


def get_args():
    help_str = 'class{0 - music, 1 - PS, 2 - dota2, 3 - PC, 4 - others}, ' \
               'platform{0 - TB, 1 - JD, 2 - XY, 3 - PDD, 4 - others}]'
    parser = argparse.ArgumentParser(description=help_str)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--csv', action='store_true', help='操作csv, 添加消费项')
    group.add_argument('--json', action='store_true', help='操作json, 总结模块')

    # common args
    parser.add_argument('--show', action='store_true', help='查看csv/账户总览')
    parser.add_argument('--sort', action='store_true', help='按消费时间排序')
    parser.add_argument('--special', action='store_true', help='特殊操作')

    # csv add item
    parser.add_argument('--sell', action='store_true', help='卖出，默认为买入')
    parser.add_argument('--close_loop', action='store_true', help='需要跟踪买卖闭环')
    parser.add_argument('-n', '--name', help='商品名称')
    parser.add_argument('-p', '--platform', help='消费平台', default='0')
    parser.add_argument('-c', '--classification', help='消费大类', default='0')
    parser.add_argument('-P', '--price', type=float, help='价格')
    parser.add_argument('-d', '--date', help='买入日期，格式：20xx-xx-xx')
    parser.add_argument('-r', '--remark', help='备注')

    # json add year
    parser.add_argument('-y', '--add_year', type=int, help='json中创建一年')

    return parser.parse_args()


class CsvItem:
    def __init__(self):
        # read csv
        if os.path.exists(csv_file):
            self.df = pd.read_csv(csv_file, encoding='utf-8_sig')
        else:
            print(f'{csv_file} not exit, creat')
            self.df = pd.DataFrame(columns=['name', 'class', 'platform', 'B/S', 'price', 'closed',
                                            'profit', 'trade_date', 'record_date', 'remark', 'year'])

    def sort_csv(self):
        self.df = self.df.sort_values(by='trade_date')
        self.df.set_index(pd.Series(range(self.df.shape[0])))
        print("sort csv by date. done.")

    def show(self):
        print(self.df)
        print('total consumption:', self.df['price'].sum())
        print('\nneeded to be close_loop:')
        print(self.df[self.df['closed'] == 'N'])
        print('total consumption:', round(self.df[self.df['closed'] == 'N']['price'].sum(), 2))

    def add_item(self, args):
        item_dict = {
            'name': [args.name],
            'class': [class_dict[args.classification]],
            'platform': [pf_dict[args.platform]],
            'B/S': ['S' if args.sell else 'B'],
            'price': [args.price if args.sell else -args.price],
            'trade_date': [time_now if args.date is None else args.date],
            'remark': [np.nan if args.remark is None else args.remark],
            'record_date': [time_now],
        }

        item_dict['year'] = [item_dict['trade_date'][0].split('-')[0]]
        if args.close_loop:
            if item_dict['B/S'][0] == 'B':
                item_dict['closed'] = ['N']
                item_dict['profit'] = [item_dict['price'][0]]
            else:
                match_row = (self.df[self.df['name'] == item_dict['name'][0]])
                idx = list(match_row.index)[-1]

                assert self.df.loc[idx, 'closed'] == 'N'
                self.df.loc[idx, 'closed'] = 'Y'
                self.df.loc[idx, 'profit'] = self.df.loc[idx, 'price'] + item_dict['price'][0]
                print("close_loop found:")
                print(self.df.loc[idx], '\n')

        self.df = pd.concat([self.df, pd.DataFrame(item_dict)], ignore_index=True)

        print('add item:')
        print(self.df.iloc[len(self.df) - 1])

    def add_pc_funds(self, year):
        item_dict = {
            'name': "PC 换代",
            'class': [class_dict["3"]],
            'platform': [pf_dict["4"]],
            'B/S': ['S'],
            'price': [pc_founds],
            'trade_date': [str(year) + "-01-01"],
            'remark': [np.nan],
            'record_date': [time_now],
            'year': [year]
        }

        self.df = pd.concat([self.df, pd.DataFrame(item_dict)], ignore_index=True)

        print('\nadd item:')
        print(self.df.iloc[len(self.df) - 1])

    def save(self):
        self.df.to_csv(csv_file, index=False, encoding='utf-8_sig')

    def special_operation(self):
        # 删除最后一行
        self.df = self.df.drop([len(self.df) - 1])
        print(len(self.df))
        pass

    def get_csv(self):
        return self.df


class JsonItem:
    def __init__(self):
        # read json
        if os.path.exists(json_file):
            try:
                self.json_f = open(json_file, 'r+', encoding='utf-8')
                self.summary_dict = json.load(self.json_f)
                self.json_f.seek(0)  # 移动文件指针到头部以便写入
            except json.decoder.JSONDecodeError:
                print("An JSONDecodeError occurred,may caused by empty json file.")
                self.__creat_json()
        else:
            self.__creat_json()

    def show_summary(self, df):
        this_year = int(time_now.split('-')[0])
        print("summary of year:")
        for y in range(2018, this_year):
            print(f"year [{y}] outlay: {self.summary_dict[str(y)]['outlay']}")

        print(f"\nsummary of class (till {this_year - 1}):")
        for _, val in class_dict.items():
            total_outlay = 0
            for y in range(2018, this_year):
                total_outlay += self.summary_dict[str(y)]['class'][val]['profit']
            print(f"class [{val}] outlay: {round(total_outlay, 2)}")

        surplus_history = self.summary_dict[str(this_year)]['surplus_history']
        funds_this_year = self.summary_dict[str(this_year)]['funds']
        outlay_this_year = df[df['year'] == this_year]['price'].sum()
        net_profit = funds_this_year + outlay_this_year
        balance = net_profit + surplus_history
        print(f"\nIn year {this_year}, funds {funds_this_year}, history_surplus {surplus_history}"
              f"\noutlay till now {round(outlay_this_year, 2)}, net_profit {round(net_profit, 2)},"
              f" balance {round(balance, 2)}"
              f"\nGood luck, and to be better.")

    def add_year(self, df, year):
        self.__check_history(year)
        self.__end_last_year(df, year - 1)
        self.__add_new_year(year)

    def save(self):
        # or json_f.write(json.dumps(dict, ...))
        json.dump(self.summary_dict, self.json_f, indent=4, ensure_ascii=False, sort_keys=True)

    def special_operation(self):
        pass

    def sort_json(self):
        pass

    def __creat_json(self):
        self.json_f = open(json_file, 'w', encoding='utf-8')
        self.summary_dict = {
            '0': {
                'class': {
                    class_dict['0']: 0,
                    class_dict['1']: 0,
                    class_dict['2']: 0,
                    class_dict['3']: 0,
                    class_dict['4']: 0,
                },
                'balance': 0,
                'till': 0,
            },
        }

    def __check_history(self, year):
        for key, val in self.summary_dict.items():
            if int(key) == 0:
                pass
            elif int(key) == (year - 1):
                assert val['ended'] == False
            elif int(key) < (year - 1):
                assert val['ended'] == True
            else:
                assert 0

    def __end_last_year(self, df, last_year):
        key_last_year = ""
        for key, val in self.summary_dict.items():
            if int(key) != last_year:
                continue
            key_last_year = key
        if key_last_year == "":
            return

        df_year = df[df['year'] == last_year]
        js_last_year = self.summary_dict[str(last_year)]
        total_profit = 0
        for _, val in class_dict.items():
            df_class = df_year[df_year['class'] == val]
            js_last_year['class'][val]['cost'] = round(df_class[df_class['price'] <= 0]['price'].sum(), 2)
            js_last_year['class'][val]['earn'] = round(df_class[df_class['price'] > 0]['price'].sum(), 2)
            js_last_year['class'][val]['profit'] = round(df_class['price'].sum(), 2)
            total_profit += js_last_year['class'][val]['profit']

            self.summary_dict['0']['class'][val] += js_last_year['class'][val]['profit']
            self.summary_dict['0']['class'][val] = round(self.summary_dict['0']['class'][val], 2)

        js_last_year['outlay'] = round(total_profit, 2)
        js_last_year['net_profit'] = round(js_last_year['funds'] + js_last_year['outlay'], 2)
        js_last_year['ended'] = True

        self.summary_dict['0']['till'] = last_year
        self.summary_dict['0']['balance'] = js_last_year['funds'] + js_last_year['surplus_history'] + js_last_year['outlay']
        self.summary_dict['0']['balance'] = round(self.summary_dict['0']['balance'], 2)

        print(f"end year: {last_year}, total outlay: {js_last_year['outlay']}, balance: {self.summary_dict['0']['balance']}")
        for _, val in class_dict.items():
            print(f"{val} outlay: {js_last_year['class'][val]['profit']}")

    def __add_new_year(self, new_year):
        if new_year == 2018:
            funds = funds_one_year / 2
            surplus_history = 0
        else:
            funds = funds_one_year
            surplus_history = (self.summary_dict['0']['balance']) * 1.1

        self.summary_dict[str(new_year)] = {
            'surplus_history': round(surplus_history, 2),
            'funds': funds,
            'outlay': 0,
            'net_profit': 0,
            'ended': False,
            'class': {}
        }

        for _, val in class_dict.items():
            self.summary_dict[str(new_year)]['class'][val] = {
                'cost': 0,
                'earn': 0,
                'profit': 0,
            }

        print(f"\nadd year to json file: {new_year}, funds: {funds}, surplus_history {round(surplus_history, 2)}")


if __name__ == '__main__':
    # get input
    args = get_args()
    # creat csv item
    csv_item = CsvItem()

    if args.csv:
        if args.sort:
            csv_item.sort_csv()
        elif args.show:
            csv_item.show()
        elif args.special:
            csv_item.special_operation()
        else:
            csv_item.add_item(args)

        # save csv
        csv_item.save()

    elif args.json:
        # creat json item
        json_item = JsonItem()

        if args.show:
            json_item.show_summary(csv_item.get_csv())
        elif args.add_year is not None:
            json_item.add_year(csv_item.get_csv(), args.add_year)
            if args.add_year % 5 == 0:
                csv_item.add_pc_funds(args.add_year)
                csv_item.save()
        elif args.special:
            json_item.special_operation()
        elif args.sort:
            json_item.sort_json()
        else:
            print("unknown json args")

        # save json file
        json_item.save()

    else:
        print('unknown args')
