import { useEffect, useState } from "react";
import { Download, Plus } from "lucide-react";
import { toast } from "sonner";

type InstallPrompt = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
};

export default function PWAInstall() {
  const [prompt, setPrompt] = useState<InstallPrompt | null>(null);
  const [ios, setIos] = useState(false);
  const [installed, setInstalled] = useState(false);

  useEffect(() => {
    const isIOS = /iphone|ipad|ipod/i.test(navigator.userAgent);
    const standalone = window.matchMedia("(display-mode: standalone)").matches || Boolean((navigator as Navigator & { standalone?: boolean }).standalone);
    setIos(isIOS && !standalone);
    setInstalled(standalone);
    const capture = (event: Event) => { event.preventDefault(); setPrompt(event as InstallPrompt); };
    const done = () => { setInstalled(true); setPrompt(null); };
    window.addEventListener("beforeinstallprompt", capture);
    window.addEventListener("appinstalled", done);
    return () => { window.removeEventListener("beforeinstallprompt", capture); window.removeEventListener("appinstalled", done); };
  }, []);

  if (installed || (!prompt && !ios)) return null;
  return <button type="button" className="install-app-button" onClick={async () => {
    if (ios) {
      toast.info("على iPhone أو iPad: اضغط مشاركة في Safari، ثم اختر «إضافة إلى الشاشة الرئيسية».", { duration: 7000 });
      return;
    }
    if (!prompt) {
      toast.info("من قائمة المتصفح اختر «تثبيت التطبيق» أو «إضافة إلى الشاشة الرئيسية».");
      return;
    }
    await prompt.prompt();
    const choice = await prompt.userChoice;
    if (choice.outcome === "accepted") setInstalled(true);
    setPrompt(null);
  }}><Download size={14} /><span>تثبيت التطبيق</span><Plus size={12} className="install-plus" /></button>;
}
