"use client";

import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import Image from "next/image";
import useEmblaCarousel from "embla-carousel-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ChevronLeft, ChevronRight } from "lucide-react";

import independantImage from "@/public/images/independent-worker.jpg";
import freelanceImage from "@/public/images/freelance-worker.jpg";
import particulierImage from "@/public/images/happy-family.jpg";
import seniorImage from "@/public/images/veteran-worker.jpg";
import etudiantImage from "@/public/images/student-worker.jpg";

// Figma assets for target profiles
const profileImages = {
  independant: independantImage,
  freelance: freelanceImage,
  particulier: particulierImage,
  senior: seniorImage,
  etudiant: etudiantImage,
};

const profiles = [
  {
    id: "independant",
    title: "Indépendant",
    image: profileImages.independant,
    description: null,
    size: "small",
  },
  {
    id: "freelance",
    title: "Freelances",
    image: profileImages.freelance,
    description: null,
    size: "small",
  },
  {
    id: "particulier",
    title: "Particuliers & Familles",
    image: profileImages.particulier,
    description: "Déchargez votre esprit de la charge mentale administrative et sécurisez l'essentiel pour ceux que vous aimez.",
    size: "large",
  },
  {
    id: "senior",
    title: "Seniors",
    image: profileImages.senior,
    description: null,
    size: "small",
  },
  {
    id: "etudiant",
    title: "Étudiants",
    image: profileImages.etudiant,
    description: null,
    size: "small",
  },
];

type AssistanceFormData = {
  email: string;
  full_name: string;
  message: string;
  subject: string;
};

const initialAssistanceFormData: AssistanceFormData = {
  email: "",
  full_name: "",
  message: "",
  subject: "",
};

export function TargetAudienceSection() {
  const [emblaRef, emblaApi] = useEmblaCarousel({ 
    loop: true,
    align: "start",
    skipSnaps: false,
  });
  const [canScrollPrev, setCanScrollPrev] = useState(false);
  const [canScrollNext, setCanScrollNext] = useState(true);
  const [assistanceFormData, setAssistanceFormData] = useState<AssistanceFormData>(
    initialAssistanceFormData
  );
  const [isSubmittingAssistance, setIsSubmittingAssistance] = useState(false);
  const [assistanceStatus, setAssistanceStatus] = useState<{
    type: "success" | "error" | null;
    message: string;
  }>({
    type: null,
    message: "",
  });

  const scrollPrev = useCallback(() => emblaApi?.scrollPrev(), [emblaApi]);
  const scrollNext = useCallback(() => emblaApi?.scrollNext(), [emblaApi]);

  const onSelect = useCallback(() => {
    if (!emblaApi) return;
    setCanScrollPrev(emblaApi.canScrollPrev());
    setCanScrollNext(emblaApi.canScrollNext());
  }, [emblaApi]);

  useEffect(() => {
    if (!emblaApi) return;
    onSelect();
    emblaApi.on("select", onSelect);
    return () => {
      emblaApi.off("select", onSelect);
    };
  }, [emblaApi, onSelect]);

  const handleAssistanceFieldChange = (
    event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) => {
    const { name, value } = event.target;
    setAssistanceFormData((previousData) => ({
      ...previousData,
      [name]: value,
    }));
  };

  const handleAssistanceSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsSubmittingAssistance(true);
    setAssistanceStatus({ type: null, message: "" });

    const assistancePayload = {
      app_version: "1.0.0",
      ...assistanceFormData,
      platform: "mobile",
      user_id: 0,
    };

    try {
      console.info("[Assistance] Sending request", assistancePayload);
      const response = await fetch("https://back-end-prod.satkaar.io/meta/assistance", {
        method: "POST",
        headers: {
          accept: "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify(assistancePayload),
      });

      const rawResponseBody = await response.text();
      let parsedResponseBody: unknown = rawResponseBody;

      try {
        parsedResponseBody = rawResponseBody ? JSON.parse(rawResponseBody) : null;
      } catch {
        // Keep raw text if response is not valid JSON.
      }

      console.info("[Assistance] Response received", {
        ok: response.ok,
        status: response.status,
        statusText: response.statusText,
        body: parsedResponseBody,
      });

      if (!response.ok) {
        throw new Error("Erreur lors de l'envoi de votre demande.");
      }

      setAssistanceStatus({
        type: "success",
        message: "Votre question a bien ete envoyee.",
      });
      setAssistanceFormData(initialAssistanceFormData);
    } catch (error) {
      console.error("[Assistance] Request failed", error);
      setAssistanceStatus({
        type: "error",
        message: "Impossible d'envoyer votre demande pour le moment.",
      });
    } finally {
      setIsSubmittingAssistance(false);
    }
  };

  return (
    <section className="py-16 lg:py-24 overflow-hidden">
      <div className="container-oso">
        <motion.div
          className="mb-16 rounded-oso-s border border-gris-20 bg-white p-6 lg:p-8"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
        >
          <div className="mb-6">
            <h3 className="font-heading text-3xl font-semibold text-gris-70">
              Vous avez une question ou besoin d&apos;assistance ?
            </h3>
            <p className="mt-2 text-gris-60">
              Envoyez-nous votre demande, notre equipe vous repondra rapidement.
            </p>
          </div>

          <form className="grid gap-4" onSubmit={handleAssistanceSubmit}>
            <div className="grid gap-4 lg:grid-cols-2">
              <Input
                name="full_name"
                placeholder="Nom complet"
                value={assistanceFormData.full_name}
                onChange={handleAssistanceFieldChange}
                required
              />
              <Input
                name="email"
                type="email"
                placeholder="Email"
                value={assistanceFormData.email}
                onChange={handleAssistanceFieldChange}
                required
              />
            </div>

            <div className="grid gap-4">
              <Input
                name="subject"
                placeholder="Sujet"
                value={assistanceFormData.subject}
                onChange={handleAssistanceFieldChange}
                required
              />
            </div>

            <textarea
              name="message"
              rows={5}
              placeholder="Votre message"
              value={assistanceFormData.message}
              onChange={handleAssistanceFieldChange}
              className="w-full rounded-oso-s border border-gris-20 bg-white px-4 py-3 text-base font-body text-gris-70 placeholder:text-gris-40 transition-colors focus:outline-none focus:ring-2 focus:ring-bleu-200 focus:border-bleu-200"
              required
            />

            <div className="flex flex-col items-start gap-3">
              <Button type="submit" disabled={isSubmittingAssistance}>
                {isSubmittingAssistance ? "Envoi en cours..." : "Envoyer ma question"}
              </Button>
              {assistanceStatus.type && (
                <p
                  className={
                    assistanceStatus.type === "success"
                      ? "text-sm text-emerald-700"
                      : "text-sm text-rose-700"
                  }
                >
                  {assistanceStatus.message}
                </p>
              )}
            </div>
          </form>
        </motion.div>
      </div>

      {/* Title */}
      <div className="container-oso">
        <motion.h2
          className="font-heading font-semibold text-[39px] text-gris-70 text-center mb-12"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
        >
          OSO est fait pour vous si vous êtes...
        </motion.h2>
      </div>

      {/* Carousel */}
      <motion.div
        className="relative"
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
        transition={{ duration: 0.5, delay: 0.2 }}
      >
        {/* Navigation Buttons */}
        <div className="hidden lg:flex absolute top-1/2 -translate-y-1/2 left-4 z-10">
          <button
            onClick={scrollPrev}
            disabled={!canScrollPrev}
            className="w-12 h-12 rounded-full bg-white shadow-card flex items-center justify-center disabled:opacity-50 transition-opacity"
            aria-label="Previous slide"
          >
            <ChevronLeft className="w-6 h-6 text-gris-70" />
          </button>
        </div>
        <div className="hidden lg:flex absolute top-1/2 -translate-y-1/2 right-4 z-10">
          <button
            onClick={scrollNext}
            disabled={!canScrollNext}
            className="w-12 h-12 rounded-full bg-white shadow-card flex items-center justify-center disabled:opacity-50 transition-opacity"
            aria-label="Next slide"
          >
            <ChevronRight className="w-6 h-6 text-gris-70" />
          </button>
        </div>

        {/* Carousel Container */}
        <div className="overflow-hidden pl-8" ref={emblaRef}>
          <div className="flex gap-6 justify-center">
            {profiles.map((profile) => (
              <div
                key={profile.id}
                className={`flex-shrink-0 ${
                  profile.size === "large" ? "w-[462px]" : "w-[250px]"
                } h-[500px] relative rounded-oso-s overflow-hidden group`}
              >
                {/* Background Image */}
                <Image
                  src={profile.image}
                  alt={profile.title}
                  fill
                  className="object-cover"
                />
                
                {/* Overlay */}
                <div className="absolute inset-0 bg-black/10" />

                {/* Content with Gradient */}
                <div 
                  className="absolute bottom-0 left-0 right-0 p-3 flex flex-col gap-2"
                  style={{
                    background: "linear-gradient(0.6deg, rgba(0, 0, 0, 1) 2.5%, rgba(93, 93, 93, 0.64) 44.5%, rgba(255, 255, 255, 0) 85.4%)",
                  }}
                >
                  <h4 className="font-heading font-bold text-[25px] text-white">
                    {profile.title}
                  </h4>
                  {profile.description && (
                    <p className="text-base text-white">
                      {profile.description}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </motion.div>

      {/* Bottom CTA */}
      <div className="container-oso">
        <motion.div 
          className="flex flex-col items-center gap-6 mt-16"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.4 }}
        >
          <div className="text-center">
            <p className="font-bold text-lg text-gris-70">
              Quel que soit votre profil, O.S.O s&apos;adapte à vous.
            </p>
            <p className="text-lg text-gris-70">
              Pas l&apos;inverse.
            </p>
          </div>
          <Button>
            Télécharger maintenant
          </Button>
        </motion.div>
      </div>
    </section>
  );
}
