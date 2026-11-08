import type { ComponentType } from 'react';
import type { Question } from '../types';
import { AnswerOptionCard } from './AnswerOptionCard';

export interface QuestionRendererProps {
  question: Question;
  selected: string[];
  disabled: boolean;
  onSelect: (optionId: string) => void;
}

function SingleChoice({ question, selected, disabled, onSelect }: QuestionRendererProps) {
  return (
    <div role="radiogroup" aria-labelledby={`q-${question.id}-prompt`} className="flex flex-col gap-3">
      {question.options.map((option) => (
        <AnswerOptionCard
          key={option.id}
          name={`q-${question.id}`}
          option={option}
          checked={selected.includes(option.id)}
          disabled={disabled}
          onSelect={() => onSelect(option.id)}
        />
      ))}
    </div>
  );
}

function Unsupported() {
  return <p className="rounded-2xl bg-warning-light p-4 text-[15px] font-semibold text-warning-strong">Bu turdagi savolni hozircha ko‘rsatib bo‘lmaydi. Keyingi savolga o‘t.</p>;
}

/**
 * Answer-area renderers by question type. Adding e.g. `multiple_choice` means adding one entry here
 * (answers are already arrays end-to-end) — the engine, navigator and autosave stay untouched.
 */
const renderers: Record<string, ComponentType<QuestionRendererProps>> = {
  single_choice: SingleChoice,
};

export function getQuestionRenderer(type: string): ComponentType<QuestionRendererProps> {
  return renderers[type] ?? Unsupported;
}
