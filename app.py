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
if 'api_data' not in st.session_state:
    st.session_state.api_data = {}

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

# エラーメッセージを取得する
def get_error_message(base_url, error_code):
    try:
        response = requests.post(
            f"{base_url}/api/getErrorMessage",
            json={"errorCode": error_code},
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        data = response.json()
        if data.get('isSuccess') or data.get('errorCode') == 200:
            return True, data.get('data', '不明なエラー')
        else:
            return False, data.get('errorMsg', '不明なエラー')
    except requests.exceptions.RequestException as e:
        return False, f"API接続エラー: {str(e)}"

# システムステータスを取得する
def get_system_status(base_url):
    try:
        response = requests.get(
            f"{base_url}/api/getStatus",
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        data = response.json()
        if data.get('isSuccess'):
            return True, data.get('data', {})
        else:
            return False, data.get('errorMsg', '不明なエラー')
    except requests.exceptions.RequestException as e:
        return False, f"API接続エラー: {str(e)}"

# 機器情報を取得する
def get_machine_info(base_url):
    try:
        response = requests.get(
            f"{base_url}/api/machineInfo",
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        data = response.json()
        if data.get('isSuccess'):
            return True, data.get('data', {})
        else:
            return False, data.get('errorMsg', '不明なエラー')
    except requests.exceptions.RequestException as e:
        return False, f"API接続エラー: {str(e)}"

# 現金情報を取得する
def get_cash_info(base_url):
    try:
        response = requests.get(
            f"{base_url}/api/cashInfo",
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        data = response.json()
        if data.get('isSuccess'):
            return True, data.get('data', {})
        else:
            return False, data.get('errorMsg', '不明なエラー')
    except requests.exceptions.RequestException as e:
        return False, f"API接続エラー: {str(e)}"

# センサーステータスを取得する
def get_sensor_status(base_url):
    try:
        response = requests.get(
            f"{base_url}/api/sensorStatus",
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        data = response.json()
        if data.get('isSuccess'):
            return True, data.get('data', {})
        else:
            return False, data.get('errorMsg', '不明なエラー')
    except requests.exceptions.RequestException as e:
        return False, f"API接続エラー: {str(e)}"

# アプリケーションのタイトル
st.title("Cash Point Pay ウェブアプリケーション")

# サイドバーにタブを追加
tab_selected = st.sidebar.radio(
    "機能を選択",
    ["メイン画面", "データ取得", "システム情報", "トランザクション履歴"]
)

# 設定の確認
ensure_config()
config = load_config()

# メイン画面タブ
if tab_selected == "メイン画面":
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

# データ取得タブ
elif tab_selected == "データ取得":
    st.header("データ取得")
    
    data_type = st.selectbox(
        "取得するデータタイプ",
        ["エラーメッセージ", "システムステータス", "機器情報", "現金情報", "センサーステータス"]
    )
    
    config = load_config()
    api_url = config['api_base_url']
    
    if data_type == "エラーメッセージ":
        st.subheader("エラーメッセージ取得")
        error_code = st.text_input("エラーコード", placeholder="例: 001001")
        
        if st.button("取得", key="error_message_button"):
            if error_code:
                if not st.session_state.logged_in:
                    st.warning("先にメイン画面でログインしてください")
                else:
                    success, result = get_error_message(api_url, error_code)
                    if success:
                        st.session_state.api_data["error_message"] = result
                        st.success(f"エラーメッセージ: {result}")
                    else:
                        st.error(f"取得失敗: {result}")
            else:
                st.warning("エラーコードを入力してください")
    
    elif data_type == "システムステータス":
        st.subheader("システムステータス取得")
        
        if st.button("取得", key="system_status_button"):
            if not st.session_state.logged_in:
                st.warning("先にメイン画面でログインしてください")
            else:
                success, result = get_system_status(api_url)
                if success:
                    st.session_state.api_data["system_status"] = result
                    st.json(result)
                else:
                    st.error(f"取得失敗: {result}")
    
    elif data_type == "機器情報":
        st.subheader("機器情報取得")
        
        if st.button("取得", key="machine_info_button"):
            if not st.session_state.logged_in:
                st.warning("先にメイン画面でログインしてください")
            else:
                success, result = get_machine_info(api_url)
                if success:
                    st.session_state.api_data["machine_info"] = result
                    st.json(result)
                else:
                    st.error(f"取得失敗: {result}")
    
    elif data_type == "現金情報":
        st.subheader("現金情報取得")
        
        if st.button("取得", key="cash_info_button"):
            if not st.session_state.logged_in:
                st.warning("先にメイン画面でログインしてください")
            else:
                success, result = get_cash_info(api_url)
                if success:
                    st.session_state.api_data["cash_info"] = result
                    st.json(result)
                else:
                    st.error(f"取得失敗: {result}")
    
    elif data_type == "センサーステータス":
        st.subheader("センサーステータス取得")
        
        if st.button("取得", key="sensor_status_button"):
            if not st.session_state.logged_in:
                st.warning("先にメイン画面でログインしてください")
            else:
                success, result = get_sensor_status(api_url)
                if success:
                    st.session_state.api_data["sensor_status"] = result
                    st.json(result)
                else:
                    st.error(f"取得失敗: {result}")

# システム情報タブ
elif tab_selected == "システム情報":
    st.header("システム情報")
    
    if not st.session_state.logged_in:
        st.warning("先にメイン画面でログインしてください")
    else:
        refresh_button = st.button("情報を更新")
        
        if refresh_button or "system_status" not in st.session_state.api_data:
            config = load_config()
            api_url = config['api_base_url']
            
            # システムステータスを取得
            success, system_status = get_system_status(api_url)
            if success:
                st.session_state.api_data["system_status"] = system_status
            
            # 機器情報を取得
            success, machine_info = get_machine_info(api_url)
            if success:
                st.session_state.api_data["machine_info"] = machine_info
            
            # 現金情報を取得
            success, cash_info = get_cash_info(api_url)
            if success:
                st.session_state.api_data["cash_info"] = cash_info
        
        # システムステータスの表示
        if "system_status" in st.session_state.api_data:
            st.subheader("システムステータス")
            st.json(st.session_state.api_data["system_status"])
        
        # 機器情報の表示
        if "machine_info" in st.session_state.api_data:
            st.subheader("機器情報")
            st.json(st.session_state.api_data["machine_info"])
        
        # 現金情報の表示
        if "cash_info" in st.session_state.api_data:
            st.subheader("現金情報")
            
            # 紙幣情報
            if "note" in st.session_state.api_data["cash_info"]:
                st.write("紙幣情報:")
                note_df = pd.DataFrame(st.session_state.api_data["cash_info"]["note"])
                st.dataframe(note_df)
            
            # 硬貨情報
            if "coin" in st.session_state.api_data["cash_info"]:
                st.write("硬貨情報:")
                coin_df = pd.DataFrame(st.session_state.api_data["cash_info"]["coin"])
                st.dataframe(coin_df)

# トランザクション履歴タブ
else:
    st.header("トランザクション履歴")
    
    # トランザクションデータの読み込み
    df = load_transactions()
    
    if not df.empty:
        # 日付範囲フィルター
        if 'date' in df.columns:
            min_date = pd.to_datetime(df['日時']).min().date()
            max_date = pd.to_datetime(df['日時']).max().date()
            
            date_range = st.date_input(
                "日付範囲",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date
            )
            
            if len(date_range) == 2:
                start_date, end_date = date_range
                mask = (pd.to_datetime(df['日時']).dt.date >= start_date) & (pd.to_datetime(df['日時']).dt.date <= end_date)
                filtered_df = df[mask]
            else:
                filtered_df = df
        else:
            filtered_df = df
        
        # ステータスでフィルター
        if '応対者名' in df.columns:
            users = ['すべて'] + sorted(df['応対者名'].unique().tolist())
            selected_user = st.selectbox("応対者名でフィルター", users)
            
            if selected_user != 'すべて':
                filtered_df = filtered_df[filtered_df['応対者名'] == selected_user]
        
        # ステータスでフィルター
        if 'ステータス' in df.columns:
            statuses = ['すべて'] + sorted(df['ステータス'].unique().tolist())
            selected_status = st.selectbox("ステータスでフィルター", statuses)
            
            if selected_status != 'すべて':
                filtered_df = filtered_df[filtered_df['ステータス'] == selected_status]
        
        # データ表示
        st.dataframe(filtered_df.sort_values('日時', ascending=False), use_container_width=True)
        
        # CSVダウンロードボタン
        csv = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="CSVとしてダウンロード",
            data=csv,
            file_name="transaction_history.csv",
            mime="text/csv",
        )
    else:
        st.info("取引データがありません")
