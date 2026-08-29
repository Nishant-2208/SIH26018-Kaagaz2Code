import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

type Role = 'officer' | 'admin' | 'citizen';

interface RoleConfig {
  role: Role;
  label: string;
  badge: string;
  icon: string;
  defaultId: string;
  route: string;
  description: string;
}

const ROLES: RoleConfig[] = [
  {
    role: 'officer',
    label: 'Revenue Officer',
    badge: 'Khatoni & RoR Audits',
    icon: 'badge',
    defaultId: 'REV-WB-2026-441',
    route: '/upload',
    description: 'Digitize legacy deeds, review OCR extractions, and resolve discrepancies.',
  },
  {
    role: 'admin',
    label: 'Administrator',
    badge: 'System Governance',
    icon: 'admin_panel_settings',
    defaultId: 'ADM-ND-9901',
    route: '/admin',
    description: 'Monitor pipeline throughput, manage queues, and oversee audit logs.',
  },
  {
    role: 'citizen',
    label: 'Citizen / Public',
    badge: 'Open Registry',
    icon: 'public',
    defaultId: '',
    route: '/lookup',
    description: 'Search verified Khasra parcels, cadastral maps, and mutation status.',
  },
];

export default function LoginPage() {
  const navigate = useNavigate();

  const [selectedRole, setSelectedRole] = useState<Role>('officer');
  const [userId, setUserId] = useState<string>('REV-WB-2026-441');
  const [password, setPassword] = useState<string>('••••••••••••');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  const activeConfig = ROLES.find((r) => r.role === selectedRole)!;

  function handleRoleSwitch(role: Role) {
    setSelectedRole(role);
    const target = ROLES.find((r) => r.role === role);
    if (target) {
      setUserId(target.defaultId);
      setPassword(role === 'citizen' ? '' : '••••••••••••');
    }
  }

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);

    setTimeout(() => {
      setIsSubmitting(false);
      navigate(activeConfig.route);
    }, 400);
  }

  return (
    <div className="mx-auto flex min-h-[calc(100vh-140px)] w-full max-w-[1040px] items-center justify-center px-4 py-6 sm:px-6">
      <div className="grid w-full grid-cols-1 items-center gap-8 rounded-2xl border border-outline-variant/70 bg-surface-container-lowest p-6 shadow-sm lg:grid-cols-[0.95fr_1.05fr] lg:p-10">
        
        {/* =====================================================
            LEFT PANEL: BRAND LOGO & CONCISE DESCRIPTION
        ===================================================== */}
        <div className="flex h-full flex-col justify-between border-b border-outline-variant/60 pb-6 lg:border-b-0 lg:border-r lg:pb-0 lg:pr-10">
          <div className="space-y-4">
            
            {/* Custom Logo Integration */}
            <div className="flex items-center -ml-3">
              <img
                src="/logo.jpeg"
                alt="Kaagaz2Code Logo"
                className="h-28 w-auto max-w-[340px] object-contain drop-shadow-xs"
              />
            </div>

            {/* Concise 2-Line Summary */}
            <div className="space-y-1.5">
              <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-primary">
                National Land Records Modernization
              </p>
              <p className="text-sm leading-relaxed text-on-surface-variant">
                Digitize legacy revenue deeds, extract multi-script Khatoni records with AI, and verify cadastral GIS boundaries on a secure platform.
              </p>
            </div>

            {/* Capability Badges */}
            <div className="flex flex-wrap gap-2 pt-2">
              <span className="inline-flex items-center gap-1.5 rounded-md border border-outline-variant/60 bg-surface-container-low px-2.5 py-1 text-xs font-medium text-on-surface">
                <span className="material-symbols-outlined text-sm text-primary">document_scanner</span>
                OpenCV + Tesseract OCR
              </span>
              <span className="inline-flex items-center gap-1.5 rounded-md border border-outline-variant/60 bg-surface-container-low px-2.5 py-1 text-xs font-medium text-on-surface">
                <span className="material-symbols-outlined text-sm text-primary">layers</span>
                Cadastral GIS Mapping
              </span>
              <span className="inline-flex items-center gap-1.5 rounded-md border border-outline-variant/60 bg-surface-container-low px-2.5 py-1 text-xs font-medium text-on-surface">
                <span className="material-symbols-outlined text-sm text-primary">verified</span>
                Audit Traceability
              </span>
            </div>
          </div>

          {/* Clean Government Portal Footer */}
          <div className="mt-8 flex items-center justify-between border-t border-outline-variant/50 pt-4 text-[11px] text-outline">
            <span>Ministry of Rural Development • Land Resources</span>
            <span className="font-medium">Government of India</span>
          </div>
        </div>

        {/* =====================================================
            RIGHT PANEL: DIRECT AUTHENTICATION WORKSPACE
        ===================================================== */}
        <div className="flex flex-col justify-center lg:pl-2">
          <div className="mb-5">
            <h2 className="font-headline text-xl font-bold text-on-surface">
              Access Workspace
            </h2>
            <p className="mt-0.5 text-xs text-on-surface-variant">
              Select your authorization role to enter the secure portal.
            </p>
          </div>

          {/* Compact Role Selector */}
          <div className="grid grid-cols-3 gap-2 rounded-xl border border-outline-variant/70 bg-surface-container-low p-1.5">
            {ROLES.map((r) => {
              const isActive = selectedRole === r.role;
              return (
                <button
                  key={r.role}
                  type="button"
                  onClick={() => handleRoleSwitch(r.role)}
                  className={`flex flex-col items-center justify-center gap-1 rounded-lg py-2.5 px-2 text-center transition-all ${
                    isActive
                      ? 'bg-primary text-on-primary shadow-xs font-semibold'
                      : 'text-on-surface-variant hover:bg-surface-container hover:text-on-surface'
                  }`}
                >
                  <span className="material-symbols-outlined text-xl">
                    {r.icon}
                  </span>
                  <span className="text-[11px] font-medium leading-tight">
                    {r.label}
                  </span>
                </button>
              );
            })}
          </div>

          {/* Role Status Banner */}
          <div className="mt-4 rounded-lg border border-outline-variant/60 bg-surface-container-low p-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-on-surface">
                {activeConfig.label}
              </span>
              <span className="rounded bg-primary-fixed px-2 py-0.5 text-[10px] font-bold text-primary">
                {activeConfig.badge}
              </span>
            </div>
            <p className="mt-1 text-[11px] leading-4 text-on-surface-variant">
              {activeConfig.description}
            </p>
          </div>

          {/* Form */}
          {selectedRole !== 'citizen' ? (
            <form onSubmit={handleSubmit} className="mt-5 space-y-4">
              <div>
                <label
                  htmlFor="user-id"
                  className="mb-1 block text-[11px] font-semibold uppercase tracking-[0.08em] text-on-surface-variant"
                >
                  Official Service ID / Pen No.
                </label>
                <div className="relative">
                  <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-outline">
                    <span className="material-symbols-outlined text-lg">badge</span>
                  </span>
                  <input
                    id="user-id"
                    type="text"
                    required
                    value={userId}
                    onChange={(e) => setUserId(e.target.value)}
                    className="w-full rounded-lg border border-outline-variant bg-surface py-2.5 pl-9 pr-3 text-xs text-on-surface outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20"
                  />
                </div>
              </div>

              <div>
                <div className="mb-1 flex items-center justify-between">
                  <label
                    htmlFor="password"
                    className="block text-[11px] font-semibold uppercase tracking-[0.08em] text-on-surface-variant"
                  >
                    Authorization Passkey
                  </label>
                  <button
                    type="button"
                    className="text-[11px] font-medium text-primary hover:underline"
                  >
                    Forgot Key?
                  </button>
                </div>
                <div className="relative">
                  <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-outline">
                    <span className="material-symbols-outlined text-lg">lock</span>
                  </span>
                  <input
                    id="password"
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full rounded-lg border border-outline-variant bg-surface py-2.5 pl-9 pr-3 text-xs text-on-surface outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={isSubmitting}
                className="flex min-h-11 w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 text-xs font-bold uppercase tracking-[0.06em] text-on-primary shadow-xs transition hover:opacity-95 disabled:opacity-50"
              >
                {isSubmitting ? (
                  <>
                    <span className="material-symbols-outlined text-base animate-spin">
                      progress_activity
                    </span>
                    Authenticating Session…
                  </>
                ) : (
                  <>
                    <span className="material-symbols-outlined text-base">login</span>
                    Enter Secure Workspace
                  </>
                )}
              </button>
            </form>
          ) : (
            <div className="mt-5 space-y-4">
              <div className="rounded-lg border border-primary/20 bg-primary-fixed/30 p-4">
                <p className="text-xs font-bold text-on-surface">
                  Public Cadastral Search
                </p>
                <p className="mt-1 text-[11px] leading-4 text-on-surface-variant">
                  Access digital Khasra maps, search by Khatoni number, and verify ownership records publicly without government credentials.
                </p>
              </div>

              <button
                type="button"
                onClick={() => navigate('/lookup')}
                className="flex min-h-11 w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 text-xs font-bold uppercase tracking-[0.06em] text-on-primary shadow-xs transition hover:opacity-95"
              >
                <span>Proceed to Public Records Lookup</span>
                <span className="material-symbols-outlined text-base">
                  arrow_forward
                </span>
              </button>
            </div>
          )}

          <div className="mt-5 flex items-center justify-center gap-1 text-[11px] text-outline">
            <span className="material-symbols-outlined text-xs">lock</span>
            Encrypted End-to-End • 256-Bit SSL Secured
          </div>
        </div>

      </div>
    </div>
  );
}