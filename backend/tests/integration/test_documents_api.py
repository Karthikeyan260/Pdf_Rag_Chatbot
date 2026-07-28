import pytest

pytestmark = pytest.mark.integration

MINIMAL_PDF_BYTES = b"%PDF-1.4\n%fake-but-valid-looking-pdf-for-upload-validation-only\n%%EOF"


async def _auth_headers(client, email: str) -> dict:
    resp = await client.post("/api/v1/auth/signup", json={"email": email, "password": "s3cure-password"})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def test_upload_rejects_non_pdf(client):
    headers = await _auth_headers(client, "dana@example.com")
    resp = await client.post(
        "/api/v1/documents/upload",
        headers=headers,
        files={"files": ("notes.txt", b"just some text", "text/plain")},
    )
    assert resp.status_code == 400


async def test_upload_and_list_and_duplicate_detection(client):
    headers = await _auth_headers(client, "erin@example.com")

    first = await client.post(
        "/api/v1/documents/upload",
        headers=headers,
        files={"files": ("report.pdf", MINIMAL_PDF_BYTES, "application/pdf")},
    )
    assert first.status_code == 201
    first_doc = first.json()[0]
    assert first_doc["duplicate_of"] is None
    assert first_doc["document"]["status"] == "queued"

    second = await client.post(
        "/api/v1/documents/upload",
        headers=headers,
        files={"files": ("report_copy.pdf", MINIMAL_PDF_BYTES, "application/pdf")},
    )
    assert second.status_code == 201
    second_doc = second.json()[0]
    assert second_doc["duplicate_of"] == first_doc["document"]["id"]

    listing = await client.get("/api/v1/documents", headers=headers)
    assert listing.status_code == 200
    assert len(listing.json()) == 1  # duplicate did not create a second row

    doc_id = first_doc["document"]["id"]
    get_resp = await client.get(f"/api/v1/documents/{doc_id}", headers=headers)
    assert get_resp.status_code == 200

    delete_resp = await client.delete(f"/api/v1/documents/{doc_id}", headers=headers)
    assert delete_resp.status_code == 204


async def test_documents_are_scoped_to_owner(client):
    headers_a = await _auth_headers(client, "frank@example.com")
    headers_b = await _auth_headers(client, "grace@example.com")

    upload = await client.post(
        "/api/v1/documents/upload",
        headers=headers_a,
        files={"files": ("private.pdf", MINIMAL_PDF_BYTES, "application/pdf")},
    )
    doc_id = upload.json()[0]["document"]["id"]

    resp = await client.get(f"/api/v1/documents/{doc_id}", headers=headers_b)
    assert resp.status_code == 404
