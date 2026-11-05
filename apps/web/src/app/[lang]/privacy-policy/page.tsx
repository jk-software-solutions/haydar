import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { hasLocale } from "@/i18n/locales";

export const metadata: Metadata = {
  title: "Privacy Policy | DawamTech",
  description: "DawamTech privacy policy for attendance and workforce management.",
};

const contactEmail = "dawamtech1@gmail.com";

export default async function PrivacyPolicyPage({
  params,
}: PageProps<"/[lang]/privacy-policy">) {
  const { lang } = await params;
  if (!hasLocale(lang)) notFound();

  const ar = lang === "ar";
  const copy = ar
    ? {
        title: "سياسة الخصوصية",
        updated: "آخر تحديث: 17 أكتوبر 2026",
        intro:
          "تشرح هذه السياسة كيفية تعامل منصة DawamTech | دوام تك مع المعلومات عند استخدام تطبيق وخدمات إدارة الحضور والموظفين.",
        sections: [
          [
            "المعلومات التي نجمعها",
            "قد نجمع بيانات الحساب والهوية الوظيفية وبيانات التواصل، بيانات الشركة والفرع والوردية، سجلات الحضور والانصراف، الطلبات والمهام والمرفقات التي يرفعها المستخدم، ومعرّفات الجهاز اللازمة لتأمين الجلسة والإشعارات.",
          ],
          [
            "الموقع والحضور",
            "يجمع التطبيق الموقع التقريبي أو الدقيق عند تسجيل الحضور أو الانصراف للتحقق من نطاق الفرع. وإذا كانت جلسة حضور مفتوحة، فقد يستمر التحقق من الموقع أثناء فترة الدوام فقط عبر إشعار نظام ظاهر، لاكتشاف مغادرة نطاق الفرع عند تفعيل هذه الميزة من الشركة. لا يستخدم التطبيق الموقع للملاحة أو للتتبع خارج ساعات الدوام أو بعد إغلاق الجلسة.",
          ],
          [
            "الكاميرا والبيانات الحيوية",
            "تُستخدم الكاميرا فقط لمسح رمز QR الخاص بالفرع عند اختيار المستخدم ذلك. وقد يطلب التطبيق تأكيد البصمة من نظام الهاتف؛ لا تستلم DawamTech قوالب البصمة أو تحفظها، وإنما تتلقى نتيجة النجاح أو الفشل فقط.",
          ],
          [
            "لماذا نستخدم البيانات",
            "نستخدم البيانات لتشغيل الحضور والانصراف، إدارة الفروع والورديات والمهام والطلبات، إرسال الإشعارات، إعداد التقارير، حماية الحسابات ومنع إساءة الاستخدام، وتقديم الدعم الفني.",
          ],
          [
            "مشاركة البيانات وحمايتها",
            "تظهر البيانات للمستخدمين المخولين داخل الشركة فقط بحسب الصلاحيات. قد تتم معالجتها بواسطة مزودي الاستضافة والبريد والإشعارات والخرائط والتخزين لتقديم الخدمة. لا نبيع البيانات الشخصية. نستخدم اتصالاً مشفراً وضوابط صلاحيات وسجلات تدقيق وتدابير حماية مناسبة.",
          ],
          [
            "الاحتفاظ والحذف",
            "تتحكم الشركة المشتركة في سجلات موظفيها وفترة الاحتفاظ بها وفق التزاماتها القانونية والتعاقدية. يمكن للموظف طلب الوصول إلى بياناته أو تصحيحها أو حذفها عبر مسؤول شركته، أو التواصل معنا عند الحاجة.",
          ],
          [
            "التغييرات والتواصل",
            "قد نحدّث هذه السياسة عند تطوير الخدمة أو تغير المتطلبات. سيظهر تاريخ آخر تحديث في أعلى الصفحة. للاستفسارات المتعلقة بالخصوصية، تواصل معنا عبر البريد الإلكتروني أدناه.",
          ],
        ],
        contact: "التواصل بخصوص الخصوصية",
        language: "English",
      }
    : {
        title: "Privacy Policy",
        updated: "Last updated: 17 October 2026",
        intro:
          "This policy explains how DawamTech processes information when you use its attendance and workforce-management application and services.",
        sections: [
          [
            "Information we collect",
            "We may collect account and employment identity information, contact details, company, branch and shift data, attendance records, requests, tasks and files submitted by users, and device identifiers needed to secure sessions and deliver notifications.",
          ],
          [
            "Location and attendance",
            "The app collects approximate or precise location when a user checks in or checks out to verify the assigned branch geofence. While an attendance session is open, location may be checked only during the working session through a visible system notification to detect a geofence exit when the company enables that feature. The app does not use location for navigation, outside working hours, or after the attendance session closes.",
          ],
          [
            "Camera and biometrics",
            "The camera is used only to scan a branch QR code when the user chooses that method. The app may request biometric confirmation from the device operating system; DawamTech does not receive or store biometric templates and receives only a success or failure result.",
          ],
          [
            "Why we use information",
            "We use information to operate attendance, branches, shifts, tasks and requests; send notifications; generate reports; protect accounts and prevent misuse; and provide support.",
          ],
          [
            "Sharing and protection",
            "Information is available only to authorized users in the relevant company according to assigned permissions. It may be processed by hosting, email, notification, mapping and storage providers that help us deliver the service. We do not sell personal information. We use encrypted transport, access controls, audit logs and appropriate safeguards.",
          ],
          [
            "Retention and deletion",
            "The subscribing company controls its employee records and retention periods in line with its legal and contractual obligations. Employees may request access, correction or deletion through their company administrator, or contact us when needed.",
          ],
          [
            "Changes and contact",
            "We may update this policy as the service or requirements change. The latest update date appears at the top of this page. Contact us at the email below for privacy questions.",
          ],
        ],
        contact: "Privacy contact",
        language: "العربية",
      };

  return (
    <main className="portal-shell">
      <article className="portal-card wide privacy-policy">
        <header className="privacy-policy-header">
          <div>
            <p className="privacy-policy-brand">DawamTech | دوام تك</p>
            <h1>{copy.title}</h1>
            <p className="privacy-policy-updated">{copy.updated}</p>
          </div>
          <a className="privacy-policy-language" href={`/${ar ? "en" : "ar"}/privacy-policy`}>
            {copy.language}
          </a>
        </header>
        <p className="privacy-policy-intro">{copy.intro}</p>
        <div className="privacy-policy-sections">
          {copy.sections.map(([heading, body]) => (
            <section key={heading}>
              <h2>{heading}</h2>
              <p>{body}</p>
            </section>
          ))}
        </div>
        <footer className="privacy-policy-contact">
          <strong>{copy.contact}</strong>
          <a href={`mailto:${contactEmail}`}>{contactEmail}</a>
        </footer>
      </article>
    </main>
  );
}
