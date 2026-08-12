//APIのURL
const API_BASE_URL = "http://localhost:5001/api/faqs";

//export:この関数を別のファイルでも使えるようにする
//async:処理に時間がかかるための準備
//await:すぐに結果が来なくてもレスポンス来るまで待つ

//FAQ一覧取得
export async function getFaqList() { 
    const response = await fetch(API_BASE_URL);

    if (!response.ok) { //ステータスが200番台か
        throw new Error("FAQ一覧の取得に失敗しました");
    }

    return await response.json();
}

//FAQ新規作成
export async function createFaq(faq){

    //API通信(Flaskへアクセス)
    const response = await fetch (API_BASE_URL, { 
        method: "POST",
        headers: { //これから送るデータがJSONであるという宣言
          "Content-Type": "application/json"  
        },
        body: JSON.stringify(faq) //JavaScripitオブジェクト→JSONに変換
    });

    if (!response.ok) { //ステータスが200番台か
        throw new Error("FAQの登録に失敗しました");
    }

    return await response.json();
}

//FAQ編集
export async function updateFaq(id, faq) {

    //API通信
    const response = await fetch (`${API_BASE_URL}/${id}`, {
        method: "PUT",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(faq)
    });

    if (!response.ok) {
        throw new Error("FAQ更新に失敗しました");
    }

    return await response.json();
}

//FAQ削除
export async function deleteFaq(id, faq) {

    //API通信
    const response = await fetch (`${API_BASE_URL}/${id}`, {
        method: "DELETE",
    });

    if (!response.ok) {
        throw new Error("FAQ削除に失敗しました");
    }

    return await response.json();
}