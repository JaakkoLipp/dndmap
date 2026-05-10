function encodeAscii(value: string) {
  return new TextEncoder().encode(value);
}

function decodeBase64Image(dataUrl: string) {
  const [, base64] = dataUrl.split(",");
  const binary = atob(base64 ?? "");
  const bytes = new Uint8Array(binary.length);

  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }

  return bytes;
}

function concatBytes(parts: Uint8Array[]) {
  const length = parts.reduce((total, part) => total + part.length, 0);
  const bytes = new Uint8Array(length);
  let offset = 0;

  parts.forEach((part) => {
    bytes.set(part, offset);
    offset += part.length;
  });

  return bytes;
}

function makePdfBlob(canvas: HTMLCanvasElement) {
  const jpegBytes = decodeBase64Image(canvas.toDataURL("image/jpeg", 0.92));
  const aspectRatio = canvas.width / canvas.height;
  const maxPageSize = 1440;
  const pageWidth = aspectRatio >= 1 ? maxPageSize : maxPageSize * aspectRatio;
  const pageHeight = aspectRatio >= 1 ? maxPageSize / aspectRatio : maxPageSize;
  const drawCommand = [
    "q",
    `${pageWidth.toFixed(2)} 0 0 ${pageHeight.toFixed(2)} 0 0 cm`,
    "/Im0 Do",
    "Q",
    "",
  ].join("\n");
  const objects: Uint8Array[] = [
    encodeAscii("1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"),
    encodeAscii("2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"),
    encodeAscii(
      [
        "3 0 obj",
        `<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ${pageWidth.toFixed(2)} ${pageHeight.toFixed(2)}]`,
        "/Resources << /XObject << /Im0 4 0 R >> >> /Contents 5 0 R >>",
        "endobj",
        "",
      ].join("\n")
    ),
    concatBytes([
      encodeAscii(
        [
          "4 0 obj",
          `<< /Type /XObject /Subtype /Image /Width ${canvas.width} /Height ${canvas.height}`,
          `/ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length ${jpegBytes.length} >>`,
          "stream",
          "",
        ].join("\n")
      ),
      jpegBytes,
      encodeAscii("\nendstream\nendobj\n"),
    ]),
    encodeAscii(
      `5 0 obj\n<< /Length ${encodeAscii(drawCommand).length} >>\nstream\n${drawCommand}endstream\nendobj\n`
    ),
  ];
  const header = encodeAscii("%PDF-1.4\n");
  const offsets: number[] = [];
  let byteOffset = header.length;

  objects.forEach((object) => {
    offsets.push(byteOffset);
    byteOffset += object.length;
  });

  const xrefOffset = byteOffset;
  const xref = encodeAscii(
    [
      "xref",
      "0 6",
      "0000000000 65535 f ",
      ...offsets.map((offset) => `${String(offset).padStart(10, "0")} 00000 n `),
      "trailer",
      "<< /Size 6 /Root 1 0 R >>",
      "startxref",
      String(xrefOffset),
      "%%EOF",
    ].join("\n")
  );

  return new Blob([concatBytes([header, ...objects, xref]) as BlobPart], {
    type: "application/pdf",
  });
}

export function downloadCanvasAsPdf(canvas: HTMLCanvasElement, filename: string) {
  const url = URL.createObjectURL(makePdfBlob(canvas));
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}
