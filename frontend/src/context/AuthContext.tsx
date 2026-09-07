import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import * as authApi from "@/api/auth";
import { getToken, setToken, setUnauthorizedHandler } from "@/api/client";

interface AuthContextValue {
  token: string | null;
  isAuthenticated: boolean;
  userId: string | null;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string) => Promise<authApi.SignupResponse>;
  verifyOtp: (email: string, otp: string) => Promise<void>;
  resendOtp: (email: string) => Promise<authApi.MessageResponse>;
  signOut: () => void;
  sessionExpired: boolean;
  clearSessionExpired: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

/** Read the `sub` claim without verifying — display purposes only. */
function readSubject(token: string | null): string | null {
  if (!token) return null;

  try {
    const [, payload] = token.split(".");
    if (!payload) return null;
    const decoded = JSON.parse(
      atob(payload.replace(/-/g, "+").replace(/_/g, "/")),
    );
    return typeof decoded.sub === "string" ? decoded.sub : null;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setTokenState] = useState<string | null>(() => getToken());
  const [sessionExpired, setSessionExpired] = useState(false);

  const signOut = useCallback(() => {
    authApi.logout();
    setTokenState(null);
  }, []);

  // A 401 from any request drops the session rather than leaving the
  // user clicking around a dead interface.
  useEffect(() => {
    setUnauthorizedHandler(() => {
      setToken(null);
      setTokenState(null);
      setSessionExpired(true);
    });

    return () => setUnauthorizedHandler(null);
  }, []);

  const signIn = useCallback(async (email: string, password: string) => {
    const result = await authApi.login(email, password);
    setTokenState(result.access_token);
    setSessionExpired(false);
  }, []);

  // Creates the account and sends the OTP email. Does not sign the user in —
  // the account isn't active until the code is verified.
  const signUp = useCallback((email: string, password: string) => {
    return authApi.signup(email, password);
  }, []);

  // Verifies the OTP and, on success, signs the user straight in.
  const verifyOtp = useCallback(async (email: string, otp: string) => {
    const result = await authApi.verifyOtp(email, otp);
    setTokenState(result.access_token);
    setSessionExpired(false);
  }, []);

  const resendOtp = useCallback((email: string) => {
    return authApi.resendOtp(email);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      token,
      isAuthenticated: Boolean(token),
      userId: readSubject(token),
      signIn,
      signUp,
      verifyOtp,
      resendOtp,
      signOut,
      sessionExpired,
      clearSessionExpired: () => setSessionExpired(false),
    }),
    [token, signIn, signUp, verifyOtp, resendOtp, signOut, sessionExpired],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
