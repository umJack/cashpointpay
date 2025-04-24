import streamlit as st
import pandas as pd
import requests
import json
import os
from datetime import datetime

# アプリケーションの設定
st.set_page_config(
    page_title="Cash Point Pay ウェブアプリケーション",
    page_icon="💰",
    layout="wide"
)

# セッション状態の初期化
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# 設定ファイルのパス
CONFIG_FILE = "config.json"
TRANSACTION_FILE = "transactions.csv"

# 初期設定の確認と作成
def ensure_config():
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
        st.success("デフォルト設定ファイルを作成しました")
    
    if not os.path.exists(TRANSACTION_FILE):
        df = pd.DataFrame(columns=[
            '日時', '応対者名', 'お支払先', '勘定項目', '出金金額', 'UUID', 'ステータス'
        ])
        df.to_csv(TRANSACTION_FILE, index=False)
        st.success("トランザクションファイルを作成しました")

# 設定を読み込む
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {
        "api_base_url": "http://127.0.0.1:8080",
        "auth": {
            "username": "admin",
            "password": "0000"
        }
    }

# トランザクションを読み込む
def load_transactions():
    if os.path.exists(TRANSACTION_FILE):
        return pd.read_csv(TRANSACTION_FILE)
    return pd.DataFrame(columns=[
        '日時', '応対者名', 'お支払先', '勘定項目', '出金金額', 'UUID', 'ステータス'
    ])

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
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    df.to_csv(TRANSACTION_FILE, index=False)
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

# アプリケーションのタイトル
st.title("Cash Point Pay ウェブアプリケーション")

# 設定の確認
ensure_config()
config = load_config()

# 2カラムレイアウト
col1, col2 = st.columns(2)

# 設定パネル (左カラム)
with col1:
    st.header("API設定")
    
    api_url = st.text_input("API URL", value=config['api_base_url'], placeholder="http://127.0.0.1:8080")
    username = st.text_input("ユーザー名", value=config['auth']['username'], placeholder="admin")
    password = st.text_input("パスワード", value=config['auth']['password'], type="password")
    
    col1_1, col1_2 = st.columns(2)
    with col1_1:
        if st.button("設定保存", type="primary"):
            new_config = {
                "api_base_url": api_url,
                "auth": {
                    "username": username,
                    "password": password
                }
            }
            with open(CONFIG_FILE, 'w') as f:
                json.dump(new_config, f, indent=2)
            st.success("設定を保存しました")
    
    with col1_2:
        if st.button("ログイン"):
            success, message = api_login(api_url, username, password)
            if success:
                st.session_state.logged_in = True
                st.success(message)
            else:
                st.error(message)

# 出金パネル (右カラム)
with col2:
    st.header("出金操作")
    
    user_name = st.text_input("応対者名", placeholder="山田太郎")
    payee = st.text_input("お支払先", placeholder="株式会社〇〇")
    account_item = st.selectbox("勘定項目", options=['会議費', '交通費', '接待費', '消耗品費', 'その他'])
    amount = st.text_input("出金金額", placeholder="1000")
    
    col2_1, col2_2 = st.columns(2)
    with col2_1:
        withdraw_button = st.button("出金実行", disabled=not st.session_state.logged_in)
        if withdraw_button:
            # 入力チェック
            if not user_name:
                st.error("応対者名を入力してください")
            elif not payee:
                st.error("お支払先を入力してください")
            else:
                try:
                    amount_val = int(amount)
                    if amount_val <= 0:
                        st.error("出金金額は0より大きい値を入力してください")
                    else:
                        # 出金処理実行
                        success, uuid, message = execute_withdrawal(api_url, amount)
                        if success and uuid:
                            # トランザクション保存
                            save_transaction(
                                user_name,
                                payee,
                                account_item,
                                amount,
                                uuid,
                                "出金処理中"
                            )
                            st.success(message)
                        else:
                            st.error(message)
                except ValueError:
                    st.error("出金金額は数値を入力してください")
    
    with col2_2:
        if st.button("データ更新"):
            df = load_transactions()
            
            # 未完了のトランザクションのステータスを更新
            updated = False
            for index, row in df.iterrows():
                if row['ステータス'] != "完了" and row['ステータス'] != "失敗":
                    success, status = check_transaction_status(api_url, row['UUID'])
                    if success:
                        if status in ["payment is completed", "Success"]:
                            df.at[index, 'ステータス'] = "完了"
                            updated = True
                        elif status in ["Payment Error", "user cancelled", "no change"]:
                            df.at[index, 'ステータス'] = "失敗"
                            updated = True
            
            if updated:
                df.to_csv(TRANSACTION_FILE, index=False)
                st.success("トランザクションステータスを更新しました")

# トランザクション一覧
st.header("最近の取引")
df = load_transactions()
if not df.empty:
    st.dataframe(
        df.sort_values('日時', ascending=False).head(10),
        use_container_width=True
    )
else:
    st.info("取引データがありません")
