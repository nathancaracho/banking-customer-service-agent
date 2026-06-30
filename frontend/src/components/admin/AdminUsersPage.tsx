import { useCallback, useEffect, useRef, useState } from 'react'
import {
  listUsers,
  getUserRoles,
  getUserFinancialSummary,
  updateUserRoles,
} from '@/api'
import type {
  AdminUser,
  AvailableRole,
  Session,
  UserFinancialSummary,
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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Skeleton } from '@/components/ui/skeleton'
import { UsersIcon, ShieldCheckIcon, CheckIcon, XIcon } from 'lucide-react'

const ALL_ROLES: AvailableRole[] = ['customer', 'manager', 'admin']

type AdminUsersPageProps = {
  session: Session
}

export function AdminUsersPage({ session }: AdminUsersPageProps) {
  const [users, setUsers] = useState<AdminUser[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectedUser, setSelectedUser] = useState<AdminUser | null>(null)
  const [loadingRoles, setLoadingRoles] = useState(false)
  const [editingRoles, setEditingRoles] = useState<AvailableRole[]>([])
  const [saving, setSaving] = useState(false)
  const [financialSummary, setFinancialSummary] =
    useState<UserFinancialSummary | null>(null)
  const mountedRef = useRef(true)

  const isManagerOrAdmin = session.roles.some(
    (role) => role === 'manager' || role === 'admin',
  )
  const isAdmin = session.roles.includes('admin')

  const loadUsers = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await listUsers(session.accessToken)
      if (mountedRef.current) {
        setUsers(data)
      }
    } catch (loadError) {
      if (mountedRef.current) {
        if (
          loadError instanceof Error &&
          loadError.message.includes('HTTP 404')
        ) {
          setUsers([])
          setError('Endpoints administrativos ainda não disponíveis.')
        } else {
          setError(
            loadError instanceof Error
              ? loadError.message
              : 'Falha ao carregar usuários',
          )
        }
      }
    } finally {
      if (mountedRef.current) {
        setLoading(false)
      }
    }
  }, [session.accessToken])

  useEffect(() => {
    mountedRef.current = true
    void loadUsers()
    return () => {
      mountedRef.current = false
    }
  }, [loadUsers])

  const openUserRoles = async (user: AdminUser) => {
    setSelectedUser(user)
    setLoadingRoles(true)
    setFinancialSummary(null)
    try {
      const [roles, summary] = await Promise.all([
        getUserRoles(session.accessToken, user.id),
        getUserFinancialSummary(session.accessToken, user.id),
      ])
      setEditingRoles(roles.map((r) => r.name))
      setFinancialSummary(summary)
    } catch {
      setEditingRoles(user.roles as AvailableRole[])
    } finally {
      setLoadingRoles(false)
    }
  }

  const toggleRole = (role: AvailableRole) => {
    if (!isAdmin) return
    setEditingRoles((current) =>
      current.includes(role)
        ? current.filter((r) => r !== role)
        : [...current, role],
    )
  }

  const saveRoles = async () => {
    if (!selectedUser || !isAdmin) return
    setSaving(true)
    try {
      await updateUserRoles(session.accessToken, selectedUser.id, editingRoles)
      setUsers((current) =>
        current.map((u) =>
          u.id === selectedUser.id ? { ...u, roles: editingRoles } : u,
        ),
      )
      setSelectedUser(null)
    } catch {
      setError('Falha ao atualizar roles.')
    } finally {
      setSaving(false)
    }
  }

  if (!isManagerOrAdmin) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center">
          <ShieldCheckIcon className="mx-auto mb-4 size-10 text-muted-foreground" />
          <h1 className="text-xl font-semibold">Acesso restrito</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Somente gerentes e administradores podem acessar esta área.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center gap-3">
        <div className="flex size-10 items-center justify-center rounded-xl bg-orange-500 text-white">
          <UsersIcon className="size-5" />
        </div>
        <div>
          <h1 className="text-2xl font-semibold">Administração de Usuários</h1>
          <p className="text-sm text-muted-foreground">
            Gerencie usuários e suas permissões de acesso.
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

      <Card>
        <CardHeader>
          <CardTitle>Usuários</CardTitle>
          <CardDescription>Lista de todos os usuários do sistema.</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="space-y-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="flex items-center gap-4">
                  <Skeleton className="h-10 w-10 rounded-full" />
                  <div className="space-y-2">
                    <Skeleton className="h-4 w-40" />
                    <Skeleton className="h-3 w-24" />
                  </div>
                </div>
              ))}
            </div>
          ) : users.length === 0 ? (
            <div className="py-8 text-center text-sm text-muted-foreground">
              Nenhum usuário encontrado.
            </div>
          ) : (
            <div className="space-y-2">
              {users.map((user) => (
                <button
                  key={user.id}
                  onClick={() => openUserRoles(user)}
                  className="flex w-full items-center gap-4 rounded-lg border p-4 text-left transition-colors hover:bg-muted/50"
                >
                  <div className="flex size-10 items-center justify-center rounded-full bg-muted text-sm font-medium">
                    {user.display_name
                      .split(' ')
                      .map((n) => n[0])
                      .join('')
                      .slice(0, 2)
                      .toUpperCase()}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="font-medium">{user.display_name}</p>
                    <p className="text-xs text-muted-foreground">{user.id}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant={user.is_active ? 'default' : 'secondary'}>
                      {user.is_active ? 'Ativo' : 'Inativo'}
                    </Badge>
                    {user.roles.map((role) => (
                      <Badge key={role} variant="outline" className="capitalize">
                        {role}
                      </Badge>
                    ))}
                  </div>
                </button>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog
        open={selectedUser !== null}
        onOpenChange={(open) => {
          if (!open) setSelectedUser(null)
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Configuração do usuário</DialogTitle>
            <DialogDescription>
              {selectedUser && (
                <>
                  Veja as roles e os dados de conta de{' '}
                  <strong>{selectedUser.display_name}</strong> ({selectedUser.id}).
                </>
              )}
            </DialogDescription>
          </DialogHeader>

          {loadingRoles ? (
            <div className="space-y-3 py-4">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : (
            <div className="space-y-5 py-4">
              {financialSummary && (
                <Card className="bg-muted/20">
                  <CardHeader>
                    <CardTitle>Dados da conta</CardTitle>
                    <CardDescription>
                      Visão resumida da situação financeira do usuário.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="grid gap-3 text-sm md:grid-cols-2">
                    <div>
                      <p className="text-muted-foreground">Saldo</p>
                      <p className="font-medium">R$ {financialSummary.balance}</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Limite atual</p>
                      <p className="font-medium">
                        R$ {financialSummary.current_limit}
                      </p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Limite máximo elegível</p>
                      <p className="font-medium">
                        R$ {financialSummary.max_eligible_limit}
                      </p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Falta para o teto</p>
                      <p className="font-medium">
                        R$ {financialSummary.missing_to_max_eligible}
                      </p>
                    </div>
                    <div className="md:col-span-2">
                      <p className="text-muted-foreground">Como adicionar mais</p>
                      <p className="font-medium">
                        {financialSummary.increase_instructions}
                      </p>
                    </div>
                  </CardContent>
                </Card>
              )}

              <Card>
                <CardHeader>
                  <CardTitle>Roles</CardTitle>
                  <CardDescription>
                    Gerentes e administradores podem revisar perfis; apenas admin
                    altera roles.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3 px-0">
                  {ALL_ROLES.map((role) => {
                    const isSelected = editingRoles.includes(role)
                    return (
                      <button
                        key={role}
                        onClick={() => toggleRole(role)}
                        disabled={!isAdmin}
                        className={`flex w-full items-center justify-between rounded-lg border p-3 text-left transition-colors ${
                          isSelected
                            ? 'border-orange-500 bg-orange-500/5'
                            : 'border-border'
                        } ${!isAdmin ? 'cursor-not-allowed opacity-60' : 'hover:bg-muted/50'}`}
                      >
                        <div>
                          <p className="font-medium capitalize">{role}</p>
                          <p className="text-xs text-muted-foreground">
                            {role === 'customer'
                              ? 'Acesso aos próprios dados'
                              : role === 'manager'
                                ? 'Acesso a dados de terceiros'
                                : 'Acesso administrativo completo'}
                          </p>
                        </div>
                        <div
                          className={`flex size-6 items-center justify-center rounded-md ${
                            isSelected ? 'bg-orange-500 text-white' : 'bg-muted'
                          }`}
                        >
                          {isSelected && <CheckIcon className="size-4" />}
                        </div>
                      </button>
                    )
                  })}
                </CardContent>
              </Card>
            </div>
          )}

          <DialogFooter>
            <Button variant="outline" onClick={() => setSelectedUser(null)}>
              Cancelar
            </Button>
            {isAdmin && (
              <Button onClick={saveRoles} disabled={saving}>
                {saving ? 'Salvando...' : 'Salvar'}
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
