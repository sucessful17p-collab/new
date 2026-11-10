# Uliya integration

The demo adapter reports a disconnected state. The API exposes the capability labels in the supplied brief (`ug-filesystem` → `file-agent`, `ug-document` → `document-agent`, `ug-knowledge` → `knowledge-agent`) and their example operations for transparency only. No live command, endpoint, or NAS connection is assumed. Implement `RealUliyaAdapter` only after the official SDK/API contract and authentication flow are available. Any persistence operation must require explicit approval and a confirmed destination; this build does not write to a NAS.
