import { useCallback, useEffect, useRef, useState } from 'react'
import {
  deleteKnowledgeDocument,
  getKnowledgeDocument,
  listKnowledgeDocuments,
  reprocessKnowledgeDocument,
  updateKnowledgeDocumentStatus,
  uploadKnowledgeDocument,
} from '@/api'
import type {
  KnowledgeDocument,
  KnowledgeDocumentDetail,
  Session,
} from '@/types'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { BookOpenIcon, RefreshCcwIcon, Trash2Icon, XIcon } from 'lucide-react'

type KnowledgeBasePageProps = {
  session: Session
}

export function KnowledgeBasePage({ session }: KnowledgeBasePageProps) {
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([])
  const [selectedDocument, setSelectedDocument] =
    useState<KnowledgeDocumentDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadingDetail, setLoadingDetail] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [title, setTitle] = useState('')
  const [source, setSource] = useState('manual_upload')
  const [active, setActive] = useState(true)
  const [file, setFile] = useState<File | null>(null)
  const [reprocessFile, setReprocessFile] = useState<File | null>(null)
  const mountedRef = useRef(true)

  const loadDocuments = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await listKnowledgeDocuments(session.accessToken)
      if (mountedRef.current) {
        setDocuments(data)
      }
      return data
    } catch (loadError) {
      if (mountedRef.current) {
        setError(
          loadError instanceof Error
            ? loadError.message
            : 'Falha ao carregar documentos',
        )
      }
      return []
    } finally {
      if (mountedRef.current) {
        setLoading(false)
      }
    }
  }, [session.accessToken])

  const openDocument = useCallback(
    async (documentId: string) => {
      setLoadingDetail(true)
      setError('')
      try {
        const detail = await getKnowledgeDocument(session.accessToken, documentId)
        if (mountedRef.current) {
          setSelectedDocument(detail)
        }
      } catch (loadError) {
        if (mountedRef.current) {
          setError(
            loadError instanceof Error
              ? loadError.message
              : 'Falha ao carregar detalhes',
          )
        }
      } finally {
        if (mountedRef.current) {
          setLoadingDetail(false)
        }
      }
    },
    [session.accessToken],
  )

  useEffect(() => {
    mountedRef.current = true
    void loadDocuments()
    return () => {
      mountedRef.current = false
    }
  }, [loadDocuments])

  const refreshAndKeepSelection = useCallback(async () => {
    const nextDocuments = await loadDocuments()
    if (selectedDocument) {
      const stillExists = nextDocuments.some(
        (document) => document.document_id === selectedDocument.document_id,
      )
      if (stillExists) {
        await openDocument(selectedDocument.document_id)
      } else {
        setSelectedDocument(null)
      }
    }
  }, [loadDocuments, openDocument, selectedDocument])

  const submitUpload = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!file || submitting) return
    setSubmitting(true)
    setError('')
    setSuccess('')
    try {
      await uploadKnowledgeDocument(session.accessToken, {
        file,
        title,
        source,
        active,
      })
      setTitle('')
      setSource('manual_upload')
      setActive(true)
      setFile(null)
      await refreshAndKeepSelection()
      setSuccess('Documento enviado e ingerido com sucesso.')
    } catch (uploadError) {
      setError(
        uploadError instanceof Error
          ? uploadError.message
          : 'Falha ao enviar documento',
      )
    } finally {
      setSubmitting(false)
    }
  }

  const toggleStatus = async (document: KnowledgeDocument) => {
    if (submitting) return
    setSubmitting(true)
    setError('')
    setSuccess('')
    try {
      await updateKnowledgeDocumentStatus(
        session.accessToken,
        document.document_id,
        !document.active,
      )
      await refreshAndKeepSelection()
      setSuccess(
        document.active
          ? 'Documento desativado com sucesso.'
          : 'Documento ativado com sucesso.',
      )
    } catch (statusError) {
      setError(
        statusError instanceof Error
          ? statusError.message
          : 'Falha ao atualizar status',
      )
    } finally {
      setSubmitting(false)
    }
  }

  const removeDocument = async (document: KnowledgeDocument) => {
    if (submitting) return
    setSubmitting(true)
    setError('')
    setSuccess('')
    try {
      await deleteKnowledgeDocument(session.accessToken, document.document_id)
      await refreshAndKeepSelection()
      setSuccess('Documento removido com sucesso.')
    } catch (deleteError) {
      setError(
        deleteError instanceof Error
          ? deleteError.message
          : 'Falha ao remover documento',
      )
    } finally {
      setSubmitting(false)
    }
  }

  const submitReprocess = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!selectedDocument || !reprocessFile || submitting) return
    setSubmitting(true)
    setError('')
    setSuccess('')
    try {
      await reprocessKnowledgeDocument(
        session.accessToken,
        selectedDocument.document_id,
        {
          file: reprocessFile,
          title: selectedDocument.title,
          source: selectedDocument.source,
        },
      )
      setReprocessFile(null)
      await refreshAndKeepSelection()
      setSuccess('Documento reprocessado com nova versão.')
    } catch (reprocessError) {
      setError(
        reprocessError instanceof Error
          ? reprocessError.message
          : 'Falha ao reprocessar documento',
      )
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center gap-3">
        <div className="flex size-10 items-center justify-center rounded-xl bg-orange-500 text-white">
          <BookOpenIcon className="size-5" />
        </div>
        <div>
          <h1 className="text-2xl font-semibold">Base de conhecimento</h1>
          <p className="text-sm text-muted-foreground">
            Faça upload, acompanhe versões e controle a disponibilidade dos
            documentos usados no RAG.
          </p>
        </div>
      </div>

      {error && (
        <Card className="border-destructive/50 bg-destructive/5">
          <CardContent className="flex items-center gap-2 py-3 text-sm text-destructive">
            <XIcon className="size-4" />
            {error}
          </CardContent>
        </Card>
      )}

      {success && (
        <Card className="border-emerald-200 bg-emerald-50">
          <CardContent className="py-3 text-sm text-emerald-700">
            {success}
          </CardContent>
        </Card>
      )}

      <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <Card>
          <CardHeader>
            <CardTitle>Novo documento</CardTitle>
            <CardDescription>
              Tipos suportados: `txt` e `pdf`. O backend aplica chunking 700/200
              e gera embeddings de 768 dimensões.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form className="space-y-4" onSubmit={submitUpload}>
              <div className="space-y-2">
                <Label htmlFor="kb-file">Arquivo</Label>
                <Input
                  id="kb-file"
                  type="file"
                  accept=".txt,.pdf"
                  onChange={(event) => setFile(event.target.files?.[0] ?? null)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="kb-title">Titulo opcional</Label>
                <Input
                  id="kb-title"
                  value={title}
                  onChange={(event) => setTitle(event.target.value)}
                  placeholder="Ex.: Politica de tarifas 2026"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="kb-source">Origem</Label>
                <Input
                  id="kb-source"
                  value={source}
                  onChange={(event) => setSource(event.target.value)}
                />
              </div>
              <label className="flex items-center gap-3 text-sm">
                <input
                  type="checkbox"
                  checked={active}
                  onChange={(event) => setActive(event.target.checked)}
                />
                Publicar como documento ativo
              </label>
              <Button disabled={!file || submitting}>
                {submitting ? 'Enviando...' : 'Enviar arquivo'}
              </Button>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Documentos</CardTitle>
            <CardDescription>
              A lista mostra o estado mais recente de cada documento ingerido.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="space-y-3">
                {Array.from({ length: 4 }).map((_, index) => (
                  <Skeleton key={index} className="h-16 w-full" />
                ))}
              </div>
            ) : documents.length === 0 ? (
              <div className="py-8 text-center text-sm text-muted-foreground">
                Nenhum documento ingerido ainda.
              </div>
            ) : (
              <div className="space-y-2">
                {documents.map((document) => (
                  <button
                    key={document.document_id}
                    onClick={() => openDocument(document.document_id)}
                    className="w-full rounded-lg border p-4 text-left transition-colors hover:bg-muted/40"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="min-w-0">
                        <p className="truncate font-medium">{document.title}</p>
                        <p className="truncate text-xs text-muted-foreground">
                          {document.original_file_name}
                        </p>
                      </div>
                      <Badge variant={document.active ? 'default' : 'secondary'}>
                        {document.active ? 'Ativo' : 'Inativo'}
                      </Badge>
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2 text-xs text-muted-foreground">
                      <span>Status: {document.status}</span>
                      <span>Versao: {document.active_version}</span>
                      <span>Chunks: {document.chunk_count}</span>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Detalhes e acoes</CardTitle>
          <CardDescription>
            Selecione um documento para ver o historico de versoes e executar
            operacoes administrativas.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loadingDetail ? (
            <div className="space-y-3">
              <Skeleton className="h-20 w-full" />
              <Skeleton className="h-40 w-full" />
            </div>
          ) : !selectedDocument ? (
            <div className="py-8 text-center text-sm text-muted-foreground">
              Escolha um documento na lista para ver mais detalhes.
            </div>
          ) : (
            <div className="space-y-6">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="space-y-1">
                  <h2 className="text-lg font-semibold">{selectedDocument.title}</h2>
                  <p className="text-sm text-muted-foreground">
                    {selectedDocument.original_file_name} • {selectedDocument.source}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button
                    variant="outline"
                    disabled={submitting}
                    onClick={() => toggleStatus(selectedDocument)}
                  >
                    {selectedDocument.active ? 'Desativar' : 'Ativar'}
                  </Button>
                  <Button
                    variant="outline"
                    disabled={submitting}
                    onClick={() => removeDocument(selectedDocument)}
                  >
                    <Trash2Icon className="mr-2 size-4" />
                    Remover
                  </Button>
                </div>
              </div>

              <form className="space-y-4 rounded-lg border p-4" onSubmit={submitReprocess}>
                <div className="flex items-center gap-2">
                  <RefreshCcwIcon className="size-4 text-muted-foreground" />
                  <h3 className="font-medium">Reprocessar documento</h3>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="kb-reprocess-file">Novo arquivo da mesma referencia</Label>
                  <Input
                    id="kb-reprocess-file"
                    type="file"
                    accept=".txt,.pdf"
                    onChange={(event) =>
                      setReprocessFile(event.target.files?.[0] ?? null)
                    }
                  />
                </div>
                <Button disabled={!reprocessFile || submitting} variant="secondary">
                  {submitting ? 'Processando...' : 'Criar nova versao'}
                </Button>
              </form>

              <div className="space-y-3">
                <h3 className="font-medium">Historico de versoes</h3>
                {selectedDocument.versions.map((version) => (
                  <div
                    key={version.id}
                    className="rounded-lg border p-4 text-sm"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div className="flex items-center gap-2">
                        <Badge variant="outline">v{version.version}</Badge>
                        <Badge
                          variant={
                            version.status === 'completed' ? 'default' : 'secondary'
                          }
                        >
                          {version.status}
                        </Badge>
                      </div>
                      <span className="text-muted-foreground">
                        {new Date(version.created_at).toLocaleString('pt-BR')}
                      </span>
                    </div>
                    <div className="mt-3 flex flex-wrap gap-4 text-muted-foreground">
                      <span>Chunks: {version.chunk_count}</span>
                      <span>Dimensoes: {version.embedding_dimensions}</span>
                    </div>
                    {version.error_message && (
                      <p className="mt-3 text-destructive">{version.error_message}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
