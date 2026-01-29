/**
 * Plan Approval Component
 * Allows users to review and approve agent plans before execution
 */

import { useState } from 'react'

interface Plan {
    analysis: string
    steps: string[]
    files: { name: string; purpose: string }[]
    tests: string[]
}

interface PlanApprovalProps {
    plan: Plan
    onApprove: () => void
    onReject: (feedback: string) => void
    onModify: (modifiedPlan: Plan) => void
}

export function PlanApproval({ plan, onApprove, onReject, onModify }: PlanApprovalProps) {
    const [feedback, setFeedback] = useState('')
    const [isEditing, setIsEditing] = useState(false)
    const [editedPlan, setEditedPlan] = useState<Plan>(plan)

    const handleApprove = () => {
        if (isEditing) {
            onModify(editedPlan)
        } else {
            onApprove()
        }
    }

    const handleReject = () => {
        if (feedback.trim()) {
            onReject(feedback)
        }
    }

    const updateStep = (index: number, newValue: string) => {
        const newSteps = [...editedPlan.steps]
        newSteps[index] = newValue
        setEditedPlan({ ...editedPlan, steps: newSteps })
    }

    const addStep = () => {
        setEditedPlan({ ...editedPlan, steps: [...editedPlan.steps, 'New step'] })
    }

    const removeStep = (index: number) => {
        const newSteps = editedPlan.steps.filter((_, i) => i !== index)
        setEditedPlan({ ...editedPlan, steps: newSteps })
    }

    return (
        <div className="plan-approval">
            <div className="plan-header">
                <div className="plan-icon">📋</div>
                <h3>Plan Review</h3>
                <span className="plan-badge">Awaiting Approval</span>
            </div>

            {/* Analysis */}
            <div className="plan-section">
                <h4>Analysis</h4>
                <p className="plan-analysis">{plan.analysis}</p>
            </div>

            {/* Steps */}
            <div className="plan-section">
                <div className="section-header">
                    <h4>Steps ({editedPlan.steps.length})</h4>
                    {isEditing && (
                        <button className="add-btn" onClick={addStep}>+ Add Step</button>
                    )}
                </div>
                <ol className="plan-steps">
                    {editedPlan.steps.map((step, index) => (
                        <li key={index} className="plan-step">
                            {isEditing ? (
                                <div className="step-edit">
                                    <input
                                        type="text"
                                        value={step}
                                        onChange={(e) => updateStep(index, e.target.value)}
                                    />
                                    <button className="remove-btn" onClick={() => removeStep(index)}>×</button>
                                </div>
                            ) : (
                                <span>{step}</span>
                            )}
                        </li>
                    ))}
                </ol>
            </div>

            {/* Files */}
            <div className="plan-section">
                <h4>Files to Create ({plan.files.length})</h4>
                <ul className="plan-files">
                    {plan.files.map((file, index) => (
                        <li key={index} className="plan-file">
                            <code>{file.name}</code>
                            <span className="file-purpose">{file.purpose}</span>
                        </li>
                    ))}
                </ul>
            </div>

            {/* Tests */}
            <div className="plan-section">
                <h4>Tests to Run ({plan.tests.length})</h4>
                <ul className="plan-tests">
                    {plan.tests.map((test, index) => (
                        <li key={index} className="plan-test">
                            <span className="test-icon">🧪</span>
                            {test}
                        </li>
                    ))}
                </ul>
            </div>

            {/* Feedback for rejection */}
            <div className="plan-section feedback-section">
                <h4>Feedback (optional)</h4>
                <textarea
                    placeholder="Add suggestions or request changes..."
                    value={feedback}
                    onChange={(e) => setFeedback(e.target.value)}
                    rows={3}
                />
            </div>

            {/* Actions */}
            <div className="plan-actions">
                <button
                    className="btn-edit"
                    onClick={() => setIsEditing(!isEditing)}
                >
                    {isEditing ? '✓ Done Editing' : '✏️ Edit Plan'}
                </button>
                <button
                    className="btn-reject"
                    onClick={handleReject}
                    disabled={!feedback.trim()}
                >
                    ✕ Request Changes
                </button>
                <button
                    className="btn-approve"
                    onClick={handleApprove}
                >
                    ✓ Approve & Continue
                </button>
            </div>
        </div>
    )
}

export default PlanApproval
