import {useEffect, useState} from "react";
import { getFaqList } from "./api/faqApi";
import { createFaq } from "./api/faqApi";
import { updateFaq } from "./api/faqApi";
import { deleteFaq } from "./api/faqApi";

// ↓↓react-bootstrap
import Container from "react-bootstrap/Container";
import Card from "react-bootstrap/Card";
import Table from "react-bootstrap/Table";
import Button from "react-bootstrap/Button";
import Form from "react-bootstrap/Form";
import { Link } from "react-router-dom";

function FaqAdmin() {

    //useState: 画面で使うデータを保存する箱

    /*===
    一覧表示用State
    ===*/
    //APIから取得したFAQ一覧を保存
    const [faqList, setFaqList] = useState([]);
        //faqList：FAQ一覧
        //setFaqList：faqListを書き換える関数
    //API通信中かどうか
    const [isLoading, setIsLoading] = useState(true);
    //エラーメッセージを保存
    const [errorMessage, setErrorMessage] = useState("");

    /*===
    登録(CREATE)用State
    ===*/
    const [question, setQuestion] = useState("");
    const [answer, setAnswer] = useState("");
    const [hasMap, setHasMap] = useState(false);

    /*===
    編集（UPDATE)用State
    ===*/
    const [editId, setEditId] = useState(null);

    // === 一覧表示関数 ===
    const loadFaqList = async () => {
        try {
            const data = await getFaqList();
            setFaqList(data);
        } catch (error) {
            console.error("FAQ一覧取得エラー", error);
            setErrorMessage(error.message);
        } finally {
            setIsLoading(false);
        }
    };

    //=== 画面を表示した時にFAQ一覧を取得 ===
    useEffect(() => {
        loadFaqList();
    }, []);

    //API通信中
    if (isLoading) {
        return <p>FAQ一覧読み込み中...</p>;
    }

    //API通信失敗
    if (errorMessage) {
        return (
            <div>
                <p>{errorMessage}</p>
            </div>
        );
    }

    //=== FAQ新規登録 ===
    const handleCreateFaq = async () => {
        const faq = {
            question: question,
            answer: answer,
            has_map: hasMap
        }

        try {
            await createFaq(faq);
            await loadFaqList();

                //成功したら初期化
                setEditId(null);
                setQuestion("");
                setAnswer("");
                setHasMap(false);
        } catch (error) {
            console.error("FAQ登録エラー", error);
            setErrorMessage(error.message);
        }
    }


    //=== FAQ編集用のボタン（入力欄に値を表示)===
    const handleEditClick = (faq) => {
        setEditId(faq.id);
        setQuestion(faq.question);
        setAnswer(faq.answer);
        setHasMap(faq.has_map === 1);
    }
    //===キャンセル用のボタン===
    const handleCancelEdit = () => {
        setEditId(null);
        setQuestion("");
        setAnswer("");
        setHasMap(false);     
    }
    

    //=== FAQ編集 ===
    const handleUpdateFaq = async () => {
        const faq = {
            question,
            answer,
            has_map: hasMap
        }

        try {
            await updateFaq(editId, faq);
            await loadFaqList();
        
                //成功したら初期化
                setEditId(null);
                setQuestion("");
                setAnswer("");
                setHasMap(false);
        } catch (error) {
            console.error("FAQ編集エラー", error);
            setErrorMessage(error.message);
        }
    }

    //=== FAQ削除 ===
    const handleDeleteFaq = async (id) => {

        //削除確認
        const isDelete = window.confirm("本当に削除してよろしいですか？");

        if (!isDelete) {
            return;
        }

        try {
            await deleteFaq(id);

            //画面上から除外する
            setFaqList((prevFaqList) => 
                prevFaqList.filter((faq) => faq.id !== id)
            );

            window.alert("FAQを削除しました");
        } catch (error) {
            console.error("FAQ削除エラー", error);
            window.alert(error.message);
        }
    }

    //=== 画面表示 ===
    return (
        <Container className="mt-4">
            <h1 className="mb-4">FAQ管理画面</h1>

            {/*== 登録フォーム(登録・更新) ==*/}
            <Card className="mb-4">
                <Card.Header>
                    <h2 className="mb-0">FAQ登録・更新</h2>
                </Card.Header>
                <Card.Body>
                    <div>
                        <Form.Group className="mb-3">
                            <Form.Label>質問</Form.Label>
                            <Form.Control
                                type="text"
                                value={question}
                                onChange={(event) => setQuestion(event.target.value)}
                            />
                        </Form.Group>
                    </div>
                    <div>
                        <Form.Group className="mb-3">
                            <Form.Label>回答</Form.Label>
                            <Form.Control
                                as="textarea"
                                rows={3}
                                value={answer}
                                onChange={(event) => setAnswer(event.target.value)}
                            />
                        </Form.Group>
                    </div>
                    <div>
                        <Form.Group className="mb-3">
                            <Form.Check
                                type="checkbox"
                                label="地図表示"
                                checked={hasMap}
                                onChange={(event) => setHasMap(event.target.checked)}
                            />
                        </Form.Group>
                    </div>
                    <div>
                        {editId === null ? (
                            <Button variant="success" onClick={handleCreateFaq}>登録</Button>
                        ) : (
                        <div>
                            <Button variant="success" className="me-2" onClick={handleUpdateFaq}>更新</Button>
                            <Button variant="danger" onClick={handleCancelEdit}>キャンセル</Button>
                        </div>
                        )}
                    </div>
                </Card.Body>
            </Card>

            {/*== 一覧表示部分 ==*/}
            <Card>
                <Card.Header>
                    <h2 className="mb-0">FAQ一覧</h2>
                </Card.Header>
                <Card.Body>
                    <Table striped bordered hover responsive>
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>質問</th>
                                <th>回答</th>
                                <th>地図表示</th>
                                <th>編集</th>
                                <th>削除</th>
                            </tr>
                        </thead>
                        <tbody>
                            {faqList.map((faq) => (
                                <tr key={faq.id}>
                                    <td>{faq.id}</td>
                                    <td>{faq.question}</td>
                                    <td>{faq.answer}</td>
                                    <td>{faq.has_map === 1 ? "あり" : "なし"}</td>
                                    <td>
                                        <Button variant="primary" onClick={() =>handleEditClick(faq)}>編集</Button>
                                    </td>
                                    <td>
                                        <Button variant="danger" onClick={() => handleDeleteFaq(faq.id)}>削除</Button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </Table>
                </Card.Body>
            </Card>
            <Link to="/">
                <Button variant="secondary" className="mb-3">チャット画面に戻る</Button>
            </Link>
 
        </Container>
    );
}

export default FaqAdmin;