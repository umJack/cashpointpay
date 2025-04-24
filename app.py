# Cash Point Pay ウェブアプリケーション
# Google Colabで動作するウェブインターフェースを提供します

import pandas as pd
import numpy as np
import requests
import json
import os
from datetime import datetime
from google.colab import auth, drive
from google.auth import default
import gspread
import ipywidgets as widgets
from ipywidgets import GridspecLayout, Button, Layout, Box, VBox, HBox, Label, Text, Dropdown, Output
from IPython.display import HTML, display, clear_output

# 必要なライブラリをインストール
!pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib

# Google Driveをマウント
drive.mount('/content/drive')

# Google認証
auth.authenticate_user()
# 最新の認証方法を使用
credentials, _ = default()
gc = gspread.authorize(credentials)

# 設定を保存するファイル
CONFIG_FILE = '/content/drive/MyDrive/CashPointPay/config.json'
TRANSACTION_SHEET = '/content/drive/MyDrive/CashPointPay/transactions.csv'

# 初期設定の確認と作成
def ensure_config():
    # CashPointPayフォルダの確認
    folder_path = '/content/drive/MyDrive/CashPointPay'
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        print(f"フォルダを作成しました: {folder_path}")
    
    # 設定ファイルの確認
    if not os.path.exists(CONFIG_FILE):
        default_config = {
            "api_base_url": "http://127.0.0.1:8080",
            "auth": {
                "username": "admin",
                "password": "0000"
            }
        }
        with open(CONFIG_FILE, 'w') as f:
            json.dump(default_config, f, indent=2)
        print(f"デフォルト設定ファイルを作成しました: {CONFIG_FILE}")
    
    # トランザクションシートの確認
    if not os.path.exists(TRANSACTION_SHEET):
        df = pd.DataFrame(columns=[
            '日時', '応対者名', 'お支払先', '勘定項目', '出金金額', 'UUID', 'ステータス'
        ])
        df.to_csv(TRANSACTION_SHEET, index=False)
        print(f"トランザクションシートを作成しました: {TRANSACTION_SHEET}")

# 設定を読み込む
def load_config():
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

# トランザクションを読み込む
def load_transactions():
    if os.path.exists(TRANSACTION_SHEET):
        return pd.read_csv(TRANSACTION_SHEET)
    return pd.DataFrame()

# トランザクションを保存する
def save_transaction(user_name, payee, account_item, amount, uuid, status):
    df = load_transactions()
    new_row = {
        '日時': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        '応対者名': user_name,
        'お支払先': payee,
        '勘定項目': account_item,
        '出金金額': amount,
        'UUID': uuid,
        'ステータス': status
    }
    # 新しい行を追加（append方法の更新）
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    df.to_csv(TRANSACTION_SHEET, index=False)
    return df

# APIにログインする
def api_login(base_url, username, password):
    try:
        response = requests.post(
            f"{base_url}/api/login",
            json={"account": username, "password": password},
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        data = response.json()
        if data.get('isSuccess'):
            return True, "ログインに成功しました"
        else:
            return False, f"ログインに失敗しました: {data.get('errorMsg', '不明なエラー')}"
    except requests.exceptions.RequestException as e:
        return False, f"API接続エラー: {str(e)}"

# 出金処理を実行する
def execute_withdrawal(base_url, amount):
    try:
        response = requests.post(
            f"{base_url}/api/refund",
            json={"amount": str(amount)},
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        data = response.json()
        if data.get('isSuccess'):
            return True, data.get('data', {}).get('uuid', 'Unknown'), "出金処理が開始されました"
        else:
            return False, None, f"出金処理に失敗しました: {data.get('errorMsg', '不明なエラー')}"
    except requests.exceptions.RequestException as e:
        return False, None, f"API接続エラー: {str(e)}"

# トランザクションステータスを確認する
def check_transaction_status(base_url, uuid):
    try:
        response = requests.post(
            f"{base_url}/api/query",
            json={"uuid": uuid},
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        data = response.json()
        if data.get('isSuccess'):
            info = data.get('data', {}).get('info', {})
            status = info.get('status', 'Unknown')
            return True, status
        else:
            return False, data.get('errorMsg', '不明なエラー')
    except requests.exceptions.RequestException as e:
        return False, f"API接続エラー: {str(e)}"

# HTMLウィジェットを作成するヘルパー関数
def create_html_output(html_content):
    output = Output()
    with output:
        display(HTML(html_content))
    return output

# ウェブアプリケーションのレイアウト作成
def create_app():
    ensure_config()
    config = load_config()
    
    # ウィジェットの作成
    status_output = Output()
    transaction_output = Output()
    
    # 設定パネル
    api_url_input = Text(
        value=config['api_base_url'],
        placeholder='http://127.0.0.1:8080',
        description='API URL:',
        layout=Layout(width='70%')
    )
    
    username_input = Text(
        value=config['auth']['username'],
        placeholder='admin',
        description='ユーザー名:',
        layout=Layout(width='70%')
    )
    
    password_input = Text(
        value=config['auth']['password'],
        placeholder='0000',
        description='パスワード:',
        layout=Layout(width='70%')
    )
    
    save_config_button = Button(
        description='設定保存',
        button_style='primary',
        layout=Layout(width='20%')
    )
    
    login_button = Button(
        description='ログイン',
        button_style='success',
        layout=Layout(width='20%')
    )
    
    # 出金パネル
    user_name_input = Text(
        placeholder='山田太郎',
        description='応対者名:',
        layout=Layout(width='70%')
    )
    
    payee_input = Text(
        placeholder='株式会社〇〇',
        description='お支払先:',
        layout=Layout(width='70%')
    )
    
    account_item_input = Dropdown(
        options=['会議費', '交通費', '接待費', '消耗品費', 'その他'],
        description='勘定項目:',
        layout=Layout(width='70%')
    )
    
    amount_input = Text(
        placeholder='1000',
        description='出金金額:',
        layout=Layout(width='70%')
    )
    
    withdraw_button = Button(
        description='出金実行',
        button_style='danger',
        layout=Layout(width='20%'),
        disabled=True
    )
    
    refresh_button = Button(
        description='データ更新',
        button_style='info',
        layout=Layout(width='20%')
    )
    
    # 設定保存のイベントハンドラ
    def on_save_config_clicked(b):
        with status_output:
            clear_output()
            config = {
                "api_base_url": api_url_input.value,
                "auth": {
                    "username": username_input.value,
                    "password": password_input.value
                }
            }
            try:
                with open(CONFIG_FILE, 'w') as f:
                    json.dump(config, f, indent=2)
                print("設定を保存しました。")
            except Exception as e:
                print(f"設定の保存に失敗しました: {str(e)}")
    
    # ログインのイベントハンドラ
    def on_login_clicked(b):
        with status_output:
            clear_output()
            success, message = api_login(
                api_url_input.value,
                username_input.value,
                password_input.value
            )
            print(message)
            if success:
                withdraw_button.disabled = False
            else:
                withdraw_button.disabled = True
    
    # 出金実行のイベントハンドラ
    def on_withdraw_clicked(b):
        with status_output:
            clear_output()
            # 入力チェック
            if not user_name_input.value:
                print("応対者名を入力してください。")
                return
            if not payee_input.value:
                print("お支払先を入力してください。")
                return
            try:
                amount = int(amount_input.value)
                if amount <= 0:
                    print("出金金額は0より大きい値を入力してください。")
                    return
            except ValueError:
                print("出金金額は数値を入力してください。")
                return
            
            # 出金処理実行
            success, uuid, message = execute_withdrawal(
                api_url_input.value,
                amount_input.value
            )
            print(message)
            
            if success and uuid:
                # トランザクション保存
                df = save_transaction(
                    user_name_input.value,
                    payee_input.value,
                    account_item_input.value,
                    amount_input.value,
                    uuid,
                    "出金処理中"
                )
                
                # トランザクション一覧更新
                with transaction_output:
                    clear_output()
                    display(df.sort_values('日時', ascending=False).head(10))
                
                # 入力フィールドをクリア
                user_name_input.value = ""
                payee_input.value = ""
                amount_input.value = ""
    
    # データ更新のイベントハンドラ
    def on_refresh_clicked(b):
        with transaction_output:
            clear_output()
            df = load_transactions()
            
            # 未完了のトランザクションのステータスを更新
            updated = False
            for index, row in df.iterrows():
                if row['ステータス'] != "完了" and row['ステータス'] != "失敗":
                    success, status = check_transaction_status(api_url_input.value, row['UUID'])
                    if success:
                        if status in ["payment is completed", "Success"]:
                            df.at[index, 'ステータス'] = "完了"
                            updated = True
                        elif status in ["Payment Error", "user cancelled", "no change"]:
                            df.at[index, 'ステータス'] = "失敗"
                            updated = True
            
            if updated:
                df.to_csv(TRANSACTION_SHEET, index=False)
            
            # 表示
            if len(df) > 0:
                display(df.sort_values('日時', ascending=False).head(10))
            else:
                print("取引データがありません。")
    
    # イベントハンドラの登録
    save_config_button.on_click(on_save_config_clicked)
    login_button.on_click(on_login_clicked)
    withdraw_button.on_click(on_withdraw_clicked)
    refresh_button.on_click(on_refresh_clicked)
    
    # レイアウトの構築
    app_title_output = create_html_output("<h1>Cash Point Pay ウェブアプリケーション</h1>")
    
    settings_title_output = create_html_output("<h2>API設定</h2>")
    settings_panel = VBox([
        settings_title_output,
        api_url_input,
        username_input,
        password_input,
        HBox([save_config_button, login_button])
    ])
    
    withdraw_title_output = create_html_output("<h2>出金操作</h2>")
    withdraw_panel = VBox([
        withdraw_title_output,
        user_name_input,
        payee_input,
        account_item_input,
        amount_input,
        HBox([withdraw_button, refresh_button])
    ])
    
    status_title_output = create_html_output("<h2>ステータス</h2>")
    status_panel = VBox([
        status_title_output,
        status_output
    ])
    
    transaction_title_output = create_html_output("<h2>最近の取引</h2>")
    transaction_panel = VBox([
        transaction_title_output,
        transaction_output
    ])
    
    # 初期データ表示
    with transaction_output:
        df = load_transactions()
        if len(df) > 0:
            display(df.sort_values('日時', ascending=False).head(10))
        else:
            print("取引データがありません。")
    
    # 最終レイアウト
    return VBox([
        app_title_output,
        HBox([settings_panel, withdraw_panel]),
        status_panel,
        transaction_panel
    ])

# アプリケーションの実行
app = create_app()
display(app)
