import type { Textbook } from "../types";

interface Props {
  textbooks: Textbook[];
  onUpload: (files: FileList) => void;
}

export default function UploadPanel({ textbooks, onUpload }: Props) {
  return (
    <section className="panel">
      <h2>教材管理</h2>
      <div className="upload-box">
        <strong>E:/textbooks</strong>
        <span>比赛 7 本医学教材从本地目录读取，PDF 不进入仓库。</span>
        <label className="file-action">
          <input
            type="file"
            multiple
            accept=".pdf,.md,.txt,.docx"
            onChange={(event) => {
              if (event.currentTarget.files?.length) onUpload(event.currentTarget.files);
              event.currentTarget.value = "";
            }}
          />
          临时上传教材
        </label>
      </div>
      <div className="book-list">
        {textbooks.length === 0 ? (
          <p className="muted">尚未解析教材。</p>
        ) : (
          textbooks.map((book) => (
            <article className="book-item" key={book.textbook_id}>
              <div>
                <strong>{book.title}</strong>
                <span>{book.filename}</span>
              </div>
              <small>{book.status} · {book.total_chars.toLocaleString()} 字</small>
            </article>
          ))
        )}
      </div>
    </section>
  );
}
