import { NOT_ADMIN_ERR_MSG, UNAUTHED_ERR_MSG } from "@shared/const";
import { PERMISSION_LABELS, hasPermission, type PermissionKey } from "@shared/rbac";
import { initTRPC, TRPCError } from "@trpc/server";
import superjson from "superjson";
import type { TrpcContext } from "./context";

const t = initTRPC.context<TrpcContext>().create({ transformer: superjson });
export const router = t.router;
export const publicProcedure = t.procedure;

const requireUser = t.middleware(async ({ ctx, next }) => {
  if (!ctx.user) throw new TRPCError({ code: "UNAUTHORIZED", message: UNAUTHED_ERR_MSG });
  if (ctx.user.suspended) throw new TRPCError({ code: "FORBIDDEN", message: "تم إيقاف هذا الحساب. تواصل مع إدارة المتجر." });
  return next({ ctx: { ...ctx, user: ctx.user } });
});

export const protectedProcedure = t.procedure.use(requireUser);

export const adminProcedure = t.procedure.use(
  t.middleware(async ({ ctx, next }) => {
    if (!ctx.user || ctx.user.role !== "admin" || ctx.user.suspended) {
      throw new TRPCError({ code: ctx.user ? "FORBIDDEN" : "UNAUTHORIZED", message: NOT_ADMIN_ERR_MSG });
    }
    if (ctx.user.mustChangePassword) {
      throw new TRPCError({ code: "PRECONDITION_FAILED", message: "يجب تغيير كلمة المرور المؤقتة أولاً قبل تنفيذ أي عملية إدارية." });
    }
    return next({ ctx: { ...ctx, user: ctx.user } });
  }),
);

export function requirePermission(permission: PermissionKey) {
  return adminProcedure.use(
    t.middleware(async ({ ctx, next }) => {
      if (!ctx.user) throw new TRPCError({ code: "UNAUTHORIZED", message: NOT_ADMIN_ERR_MSG });
      const user = ctx.user;
      const isOwner = user.isOwner ?? (user.adminRole === undefined && user.role === "admin");
      const allowed = hasPermission(user.permissions, isOwner, permission);
      if (!allowed) {
        const label = PERMISSION_LABELS[permission]?.label || permission;
        throw new TRPCError({
          code: "FORBIDDEN",
          message: "ليس لديك صلاحية («" + label + "») لتنفيذ هذا الإجراء.",
        });
      }
      return next({ ctx: { ...ctx, user } });
    }),
  );
}

export function requireAnyPermission(permissions: PermissionKey[]) {
  return adminProcedure.use(
    t.middleware(async ({ ctx, next }) => {
      if (!ctx.user) throw new TRPCError({ code: "UNAUTHORIZED", message: NOT_ADMIN_ERR_MSG });
      const user = ctx.user;
      const isOwner = user.isOwner ?? (user.adminRole === undefined && user.role === "admin");
      const allowed = permissions.some(p => hasPermission(user.permissions, isOwner, p));
      if (!allowed) {
        throw new TRPCError({
          code: "FORBIDDEN",
          message: "ليس لديك الصلاحية الكافية لتنفيذ هذا الإجراء.",
        });
      }
      return next({ ctx: { ...ctx, user } });
    }),
  );
}
