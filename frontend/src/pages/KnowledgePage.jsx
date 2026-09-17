import {
  useEffect,
  useState,
} from "react";

import {
  API_URL,
} from "../config";


function formatBytes(bytes) {
  if (!bytes) {
    return "0 B";
  }

  const units = [
    "B",
    "KB",
    "MB",
    "GB",
  ];

  let value = bytes;
  let index = 0;

  while (
    value >= 1024 &&
    index < units.length - 1
  ) {
    value /= 1024;
    index += 1;
  }

  return `${value.toFixed(
    index === 0 ? 0 : 1
  )} ${units[index]}`;
}


function getErrorMessage(data) {
  if (
    typeof data?.detail === "string"
  ) {
    return data.detail;
  }

  return "Request failed.";
}


function KnowledgePage() {
  const [
    sources,
    setSources,
  ] = useState([]);

  const [
    loading,
    setLoading,
  ] = useState(true);

  const [
    uploading,
    setUploading,
  ] = useState(false);

  const [
    extractingId,
    setExtractingId,
  ] = useState(null);

  const [
    showUpload,
    setShowUpload,
  ] = useState(false);

  const [
    error,
    setError,
  ] = useState("");

  const [
    success,
    setSuccess,
  ] = useState("");

  const [
    selectedFile,
    setSelectedFile,
  ] = useState(null);

  const [
    title,
    setTitle,
  ] = useState("");

  const [
    domain,
    setDomain,
  ] = useState("windows");

  const [
    sourceType,
    setSourceType,
  ] = useState("textbook");

  const [
    authority,
    setAuthority,
  ] = useState(
    "authoritative"
  );

  const [
    edition,
    setEdition,
  ] = useState("");

  const [
    notes,
    setNotes,
  ] = useState("");


  useEffect(() => {
    loadSources();
  }, []);


  async function request(
    path,
    options = {},
  ) {
    const response = await fetch(
      `${API_URL}${path}`,
      {
        credentials: "include",
        ...options,
      }
    );

    let data = null;

    try {
      data =
        await response.json();
    } catch {
      data = null;
    }

    if (!response.ok) {
      throw new Error(
        getErrorMessage(data)
      );
    }

    return data;
  }


  async function loadSources() {
    setLoading(true);
    setError("");

    try {
      const data =
        await request(
          "/admin/knowledge/sources"
        );

      setSources(data);

    } catch (loadError) {
      setError(
        loadError.message
      );

    } finally {
      setLoading(false);
    }
  }


  function replaceSource(
    updated
  ) {
    setSources(
      (current) =>
        current.map(
          (item) =>
            item.id === updated.id
              ? updated
              : item
        )
    );
  }


  function openUpload() {
    setSelectedFile(null);
    setTitle("");
    setDomain("windows");
    setSourceType(
      "textbook"
    );
    setAuthority(
      "authoritative"
    );
    setEdition("");
    setNotes("");
    setError("");
    setSuccess("");
    setShowUpload(true);
  }


  async function uploadSource(
    event
  ) {
    event.preventDefault();

    if (
      !selectedFile ||
      !title.trim()
    ) {
      setError(
        "Select a PDF and provide a title."
      );

      return;
    }

    setUploading(true);
    setError("");
    setSuccess("");

    const formData =
      new FormData();

    formData.append(
      "title",
      title.trim()
    );

    formData.append(
      "domain",
      domain
    );

    formData.append(
      "source_type",
      sourceType
    );

    formData.append(
      "authority",
      authority
    );

    if (edition.trim()) {
      formData.append(
        "edition",
        edition.trim()
      );
    }

    if (notes.trim()) {
      formData.append(
        "notes",
        notes.trim()
      );
    }

    formData.append(
      "file",
      selectedFile
    );

    try {
      const source =
        await request(
          "/admin/knowledge/sources",
          {
            method: "POST",
            body: formData,
          }
        );

      setSources(
        (current) => [
          source,
          ...current,
        ]
      );

      setShowUpload(false);

      setSuccess(
        `${source.title} uploaded successfully.`
      );

    } catch (uploadError) {
      setError(
        uploadError.message
      );

    } finally {
      setUploading(false);
    }
  }


  async function extractSource(
    source
  ) {
    setExtractingId(
      source.id
    );

    setError("");
    setSuccess("");

    try {
      const updated =
        await request(
          `/admin/knowledge/sources/${source.id}/extract`,
          {
            method: "POST",
          }
        );

      replaceSource(
        updated
      );

      setSuccess(
        `${source.title} extracted successfully.`
      );

    } catch (extractError) {
      setError(
        extractError.message
      );

      await loadSources();

    } finally {
      setExtractingId(
        null
      );
    }
  }


  async function toggleSource(
    source
  ) {
    setError("");
    setSuccess("");

    try {
      const updated =
        await request(
          `/admin/knowledge/sources/${source.id}/toggle`,
          {
            method: "POST",
          }
        );

      replaceSource(
        updated
      );

    } catch (toggleError) {
      setError(
        toggleError.message
      );
    }
  }


  async function deleteSource(
    source
  ) {
    const confirmed =
      window.confirm(
        `Delete "${source.title}"? ` +
        "The source PDF and extracted pages will be removed."
      );

    if (!confirmed) {
      return;
    }

    setError("");
    setSuccess("");

    try {
      await request(
        `/admin/knowledge/sources/${source.id}`,
        {
          method: "DELETE",
        }
      );

      setSources(
        (current) =>
          current.filter(
            (item) =>
              item.id !== source.id
          )
      );

      setSuccess(
        `${source.title} deleted.`
      );

    } catch (deleteError) {
      setError(
        deleteError.message
      );
    }
  }


  return (
    <main className="admin-page">

      <div className="admin-heading">

        <div>

          <span className="dashboard-eyebrow">
            RAG Administration
          </span>

          <h2>
            Knowledge Base
          </h2>

          <p>
            Manage authoritative sources
            used to ground Daedalus.
          </p>

        </div>


        <button
          className="admin-primary-button"
          onClick={openUpload}
        >
          + Add Source
        </button>

      </div>


      {error && (
        <div className="admin-alert error">
          {error}
        </div>
      )}


      {success && (
        <div className="admin-alert success">
          {success}
        </div>
      )}


      {loading ? (

        <div className="admin-loading">
          Loading knowledge sources...
        </div>

      ) : sources.length === 0 ? (

        <div className="knowledge-empty">

          <h3>
            No knowledge sources yet
          </h3>

          <p>
            Upload a Windows Internals
            textbook to begin building
            Daedalus&apos;s grounded
            knowledge base.
          </p>

          <button
            className="admin-primary-button"
            onClick={openUpload}
          >
            Add first source
          </button>

        </div>

      ) : (

        <div className="knowledge-grid">

          {sources.map(
            (source) => (

            <article
              className={
                `knowledge-card ${
                  !source.enabled
                    ? "disabled"
                    : ""
                }`
              }
              key={source.id}
            >

              <div className="knowledge-card-header">

                <div>

                  <span
                    className={
                      `knowledge-status ${
                        source.status
                      }`
                    }
                  >
                    {source.status}
                  </span>

                  <h3>
                    {source.title}
                  </h3>

                </div>


                <span className="knowledge-authority">
                  {source.authority}
                </span>

              </div>


              <div className="knowledge-filename">
                {source.original_filename}
              </div>


              <div className="knowledge-metadata">

                <div>
                  <span>
                    Domain
                  </span>

                  <strong>
                    {source.domain}
                  </strong>
                </div>


                <div>
                  <span>
                    Type
                  </span>

                  <strong>
                    {source.source_type}
                  </strong>
                </div>


                <div>
                  <span>
                    Edition
                  </span>

                  <strong>
                    {source.edition ||
                      "—"}
                  </strong>
                </div>


                <div>
                  <span>
                    Size
                  </span>

                  <strong>
                    {formatBytes(
                      source.file_size
                    )}
                  </strong>
                </div>

              </div>


              <div className="knowledge-index-state">

                <div>
                  <span>
                    Pages
                  </span>

                  <strong>
                    {source.page_count ??
                      "Not extracted"}
                  </strong>
                </div>


                <div>
                  <span>
                    Chunks
                  </span>

                  <strong>
                    {source.chunk_count}
                  </strong>
                </div>

              </div>


              {source.error_message && (

                <div className="knowledge-source-error">
                  {source.error_message}
                </div>

              )}


              {source.notes && (

                <p className="knowledge-notes">
                  {source.notes}
                </p>

              )}


              <div className="knowledge-actions">

                <button
                  onClick={() =>
                    extractSource(
                      source
                    )
                  }
                  disabled={
                    extractingId ===
                    source.id
                  }
                >
                  {extractingId ===
                  source.id
                    ? "Extracting..."
                    : source.page_count
                      ? "Re-extract"
                      : "Extract"}
                </button>


                <button
                  onClick={() =>
                    toggleSource(
                      source
                    )
                  }
                >
                  {source.enabled
                    ? "Disable"
                    : "Enable"}
                </button>


                <button
                  className="danger"
                  onClick={() =>
                    deleteSource(
                      source
                    )
                  }
                >
                  Delete
                </button>

              </div>

            </article>

          ))}

        </div>

      )}


      {showUpload && (

        <div className="modal-backdrop">

          <div className="program-modal knowledge-upload-modal">

            <div className="modal-heading">

              <div>

                <span className="modal-eyebrow">
                  Knowledge Base
                </span>

                <h3>
                  Add Source
                </h3>

              </div>


              <button
                className="modal-close"
                onClick={() =>
                  setShowUpload(false)
                }
                disabled={uploading}
              >
                ×
              </button>

            </div>


            <form
              className="program-form"
              onSubmit={
                uploadSource
              }
            >

              <label>
                PDF document

                <input
                  type="file"
                  accept=".pdf,application/pdf"
                  onChange={(event) => {
                    const file =
                      event.target
                        .files?.[0]
                      || null;

                    setSelectedFile(
                      file
                    );

                    if (
                      file &&
                      !title.trim()
                    ) {
                      setTitle(
                        file.name.replace(
                          /\.pdf$/i,
                          ""
                        )
                      );
                    }
                  }}
                />
              </label>


              <label>
                Title

                <input
                  value={title}
                  onChange={(event) =>
                    setTitle(
                      event.target.value
                    )
                  }
                  maxLength={300}
                  required
                />
              </label>


              <div className="knowledge-form-grid">

                <label>
                  Domain

                  <select
                    value={domain}
                    onChange={(event) =>
                      setDomain(
                        event.target.value
                      )
                    }
                  >
                    <option value="windows">
                      Windows Internals
                    </option>

                    <option value="rust">
                      Rust
                    </option>

                    <option value="integrated">
                      Windows + Rust
                    </option>

                    <option value="general">
                      General
                    </option>
                  </select>
                </label>


                <label>
                  Source type

                  <select
                    value={sourceType}
                    onChange={(event) =>
                      setSourceType(
                        event.target.value
                      )
                    }
                  >
                    <option value="textbook">
                      Textbook
                    </option>

                    <option value="documentation">
                      Documentation
                    </option>

                    <option value="reference">
                      Reference
                    </option>

                    <option value="supplementary">
                      Supplementary
                    </option>
                  </select>
                </label>


                <label>
                  Authority

                  <select
                    value={authority}
                    onChange={(event) =>
                      setAuthority(
                        event.target.value
                      )
                    }
                  >
                    <option value="authoritative">
                      Authoritative
                    </option>

                    <option value="trusted">
                      Trusted
                    </option>

                    <option value="supplementary">
                      Supplementary
                    </option>
                  </select>
                </label>


                <label>
                  Edition

                  <input
                    value={edition}
                    onChange={(event) =>
                      setEdition(
                        event.target.value
                      )
                    }
                    placeholder="7th Edition"
                  />
                </label>

              </div>


              <label>
                Notes

                <textarea
                  value={notes}
                  onChange={(event) =>
                    setNotes(
                      event.target.value
                    )
                  }
                  rows={3}
                  placeholder={
                    "Optional notes about this source..."
                  }
                />
              </label>


              <div className="modal-actions">

                <button
                  type="button"
                  onClick={() =>
                    setShowUpload(false)
                  }
                  disabled={uploading}
                >
                  Cancel
                </button>


                <button
                  type="submit"
                  className="admin-primary-button"
                  disabled={
                    uploading ||
                    !selectedFile ||
                    !title.trim()
                  }
                >
                  {uploading
                    ? "Uploading..."
                    : "Upload Source"}
                </button>

              </div>

            </form>

          </div>

        </div>

      )}

    </main>
  );
}


export default KnowledgePage;