// Shown by every analytical page when no model is trained yet (backend 409).
export default function NeedsTraining({ goTrain }) {
  return (
    <div className="card notice">
      <h3>No trained model yet</h3>
      <p className="muted">
        The platform serves forecasts from saved LSTM + XGBoost models — but none exist yet.
        Train the models once (a one-off ~40-60s step) and every module will populate and load
        instantly afterwards.
      </p>
      <button className="primary" onClick={goTrain}>
        Go to Train Models →
      </button>
    </div>
  );
}
