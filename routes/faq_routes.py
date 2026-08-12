#== FAQ（DB）関係のAPIのみこっちで管理
from flask import Blueprint, jsonify, request
from db import get_db_connection

#Blueprint:ルーティングをconact.pyと切り分けるための箱
#jsonify:辞書をJSON形式に変換する機能

#Blueprint作成
faq_api = Blueprint(
    "faq_api",
    __name__,
    url_prefix="/api/faqs" #Blueprintに共通してつけるURL
)

#== 一覧取得 ==
@faq_api.route("", methods=["GET"])
def get_faq_list():
    #db.pyのget_db_connection()を呼び出してDB接続
    connection = get_db_connection()

    #SQL実行のためのカーソルを作成
    cursor = connection.cursor()

    #faqテーブルから一覧を取得するSQL
    sql = """
        SELECT
            id,
            question,
            answer,
            has_map,
            created_at,
            updated_at
        FROM faq
        ORDER BY id ASC
    """

    #SQLを実行
    cursor.execute(sql)

    #検索結果を全件取得
    faqs = cursor.fetchall()

    #カーソルとDB接続を終了
    cursor.close()
    connection.close()

    #取得FAQ一覧をJSON形式で返す
    return jsonify(faqs), 200


#== 詳細取得（READ) ==
@faq_api.route("/<int:faq_id>", methods=["GET"])
def get_faq_detail(faq_id):
    #db.pyのget_db_connection()を呼び出してDB接続
    connection = get_db_connection()

    #SQL実行のためのカーソルを作成
    cursor = connection.cursor()

    #指定されたIDのFAQを取得するSQL
    sql = """
        SELECT
            id,
            question,
            answer,
            has_map,
            created_at,
            updated_at
        FROM faq
        WHERE id = %s
    """

    #URLから受けとったfaq_idをSQLに渡す
    cursor.execute(sql, (faq_id,))

    #検索結果を1件取得
    faq = cursor.fetchone()

    #接続終了
    cursor.close()
    connection.close()

    #該当するFAQがない場合
    if faq is None:
        return jsonify({
            "message": "FAQ一致なし"
        }), 404
    
    #取得したFAQをJSONで返す
    return jsonify(faq), 200


#== 新規登録(CREATE) ==
@faq_api.route("", methods=["POST"]) #一覧取得と同じURL
def create_faq():
    #JSONを取得
    createdata = request.get_json()

    #JSONが送られていない場合
    if createdata is None:
        return jsonify ({
            "message": "リクエストデータがありません"
        }), 400
    
    #必須項目を取得
    question = createdata.get("question")
    answer = createdata.get("answer")
    has_map = createdata.get("has_map", False)

    #バリデーション：question（文字列でない場合）
    #isinstance:データ型がstrかどうかを確認
    if not isinstance(question, str):
        return jsonify({
            "message": "質問は文字列で入力してください"
        }), 400

    #バリデーション：answer（文字列でない場合）
    if not isinstance(answer, str):
        return jsonify({
            "message": "回答は文字列で入力してください"
        }), 400
    
    #前後の空白を削除
    question = question.strip()
    answer = answer.strip()

    #必須項目があるかチェック
    if not question or not answer:
        return jsonify({
                        "message": "質問と回答が揃っていません"
        }), 400
    
    #バリデーション：文字数チェック
    if len(question) > 255:
        return jsonify({
            "message": "255字以内で入力してください"
        }), 400
    
    #バリデーション：has_mapの値チェック
    if has_map not in (0, 1, False, True):
        return jsonify({
            "message": "地図表示フラグは0または1で指定してください"
        }), 400
    
    #bool値の場合の変換(DB登録用)
    has_map = int(has_map)

    #DB接続
    connection = get_db_connection()
    cursor = connection.cursor()

    #FAQ登録SQL
    sql = """
        INSERT INTO faq (
            question,
            answer,
            has_map
        )
        VALUES (%s, %s, %s)
    """
    #sql実行
    try:
        cursor.execute(sql, (
            question,
            answer,
            has_map
        ))

        #登録内容の確定
        connection.commit()

        #IDを取得（自動採番）
        faq_id = cursor.lastrowid
    
    #SQLエラー時
    except Exception as e:
        connection.rollback()

        return jsonify({
            "message": "エラー：FAQ登録に失敗しました",
            "error": str(e)
        }), 500

    finally:
        #DB接続終了
        cursor.close()
        connection.close()
    
    #登録結果を返す
    return jsonify({
        "message": "FAQ登録完了",
        "id": faq_id
    }), 201 #登録ではステータスコード：201が一般的

#== 更新（UPDATE）==
@faq_api.route("/<int:faq_id>", methods=["PUT"])
def update_faq(faq_id):

    #JSONを取得
    updatedata = request.get_json()

    #JSONが送られていない場合
    if updatedata is None:
        return jsonify({
            "message": "リクエストデータがありません"
        }), 400
    
    #更新項目を取得
    question = updatedata.get("question")
    answer = updatedata.get("answer")
    has_map = updatedata.get("has_map")

    #バリデーション：question（文字列でない場合）
    #isinstance:データ型がstrかどうかを確認
    if not isinstance(question, str):
        return jsonify({
            "message": "質問は文字列で入力してください"
        }), 400

    #バリデーション：answer（文字列でない場合）
    if not isinstance(answer, str):
        return jsonify({
            "message": "回答は文字列で入力してください"
        }), 400
    
    #前後の空白を削除
    question = question.strip()
    answer = answer.strip()

    #必須項目があるかチェック
    if not question or not answer:
        return jsonify({
            "message": "質問と回答が揃っていません"
        }), 400
    
    #バリデーション：文字数チェック
    if len(question) > 255:
        return jsonify({
            "message": "255字以内で入力してください"
        }), 400
    
    #バリデーション：has_mapの値チェック
    if has_map not in (0, 1, False, True):
        return jsonify({
            "message": "地図表示フラグは0または1で指定してください"
        }), 400
    
    #bool値の場合の変換(DB登録用)
    has_map = int(has_map)
    
    #DB接続
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        #更新対象が存在するか
        check_sql = """
            SELECT id
            FROM faq
            WHERE id = %s
        """
        cursor.execute(check_sql, (faq_id,))
        faq = cursor.fetchone()
        #更新対象のFAQが存在しなかった場合→更新を止める
        if faq is None:
            return jsonify({
                "message": "更新対象が存在しません"
            }), 404
        
        #バリデーション：同じ質問が存在しないか
        duplicate_sql = """
            SELECT id
            FROM faq
            WHERE question = %s
                AND id != %s
        """
        cursor.execute(
            duplicate_sql,
            (question, faq_id)
        )

        #SQL実行
        duplicate_faq = cursor.fetchone()

        #同じ質問が存在した場合→更新を止める
        if duplicate_faq is not None:
            return jsonify({
                "message": "同じ質問がすでに登録されています"
            }), 409

        #FAQ更新SQL
        update_sql = """
            UPDATE faq
            SET
                question = %s,
                answer = %s,
                has_map = %s
            WHERE id = %s
        """
        cursor.execute(
            update_sql,
            (question, answer, has_map, faq_id)
        )

        #更新内容を確定
        connection.commit()

        return jsonify({
            "message": "FAQを更新しました",
            "id": faq_id
        }), 200

    #エラー時
    except Exception as e:
        connection.rollback()

        return jsonify({
            "message": "FAQの更新に失敗しました",
            "error": str(e)
        }), 500
    
    finally:
        cursor.close()
        connection.close()

#== 削除（DELETE)==
@faq_api.route("/<int:faq_id>", methods=["DELETE"])
def delete_faq(faq_id):

    #DB接続
    connection = get_db_connection()
    cursor = connection.cursor()

    #SQLに削除対象があるか事前確認
    check_sql = """
        SELECT id
        FROM faq
        WHERE id = %s
    """

    cursor.execute(check_sql, (faq_id,))
    faq = cursor.fetchone()

    #FAQがなかった場合
    if faq is None:
        cursor.close()
        connection.close()

        return jsonify({
            "message": "FAQが存在しません"
        }), 404
    
    #削除SQL
    delete_sql = """
        DELETE FROM faq
        WHERE id = %s
    """
    cursor.execute(delete_sql, (faq_id,))

    #DBへ反映
    connection.commit()

    #接続終了
    cursor.close()
    connection.close()

    return jsonify({
        "message":"FAQ削除しました"
    }), 200


